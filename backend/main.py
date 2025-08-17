# Arquivo: backend/main.py (Versão 5.1 - Foco em Ações, Análise com 5 Frames)
import os
import json
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel
import cv2
import ollama
import numpy as np
import whisper
from contextlib import asynccontextmanager
import asyncio
import torch

# REMOVEMOS: from ultralytics import YOLO (não vamos mais usar)
from nudenet import NudeClassifier
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
import easyocr

# --- CONSTANTES ---
POLITICAS_PATH = os.path.join("backend", "politicas", "politicas.md")
VECTORSTORE_PATH = os.path.join("backend", "faiss_index")
MODELS = {}

# --- FUNÇÕES DE ANÁLISE (ESTRATÉGIA FINAL) ---

def extrair_frames_chave(video_path, num_frames_chave=5): # AUMENTADO PARA 5 FRAMES
    """
    Extrai um número definido de frames chave (default: 5), bem distribuídos.
    """
    print(f"Extraindo {num_frames_chave} frames chave...")
    if not os.path.exists(video_path): return []
    
    cap = cv2.VideoCapture(video_path)
    total_frames_video = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames_video < num_frames_chave:
        cap.release()
        return []

    indices = np.linspace(0, total_frames_video - 1, num_frames_chave, dtype=int)
    
    caminhos_dos_frames = []
    pasta_temp = os.path.join("backend", "temp_frames")
    os.makedirs(pasta_temp, exist_ok=True)
    
    for i, frame_id in enumerate(indices):
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if ret:
            frame_path = os.path.join(pasta_temp, f"{os.path.basename(video_path).replace('.', '_')}_frame_{i}.jpg")
            cv2.imwrite(frame_path, frame)
            caminhos_dos_frames.append(frame_path)
            
    cap.release()
    print(f"{len(caminhos_dos_frames)} frames chave extraídos.")
    return caminhos_dos_frames

def analise_visual_direta(lista_de_frames):
    """
    Descreve cada frame chave individualmente para o 'Juiz' analisar.
    """
    print("Iniciando análise visual direta com LLaVA...")
    if not lista_de_frames:
        return {"descricao_geral": "Nenhum frame extraído para análise."}
    
    descricoes_individuais = []
    prompt_individual = """
    Você é um sistema de moderação. Descreva esta imagem de forma clínica e anônima.
    Foque APENAS em:
    - Ações (dançando, brigando, etc.)
    - Roupas e nudez (explícita ou sugestiva)
    - Faixa etária estimada (criança, adolescente, adulto).
    - Qualquer detalhe que possa violar uma política de segurança.
    """

    # CORREÇÃO DO BUG: Usando 'lista_de_frames' em vez de 'frames_chave'
    for i, frame_path in enumerate(lista_de_frames):
        try:
            res = ollama.generate(model='llava:latest', prompt=prompt_individual, images=[frame_path], stream=False)
            descricoes_individuais.append(f"Análise da Cena {i+1}: {res['response']}")
        except Exception as e:
            descricoes_individuais.append(f"Cena {i+1}: Erro - {e}")
    
    descricao_final = "\n".join(descricoes_individuais)
    print(f"Descrição visual final: {descricao_final[:300]}...")
    return {"descricao_geral": descricao_final}

def analisar_video_localmente(caminho_do_video, models):
    print(f"\n--- Analisando vídeo: {os.path.basename(caminho_do_video)} ---")
    
    frames = extrair_frames_chave(caminho_do_video) # Usa a extração de 5 frames
    
    analise_visual = analise_visual_direta(frames) # Analisa os 5 frames
    
    textos = leitura_de_texto_easyocr(frames, models['easyocr'])
    score_nudez = deteccao_nudez_nudenet(frames, models['nudenet'])
    transcricao = transcricao_de_audio_whisper(caminho_do_video, models['whisper'])
    eh_menor, resumo_facial = analise_facial_deepface(frames)
    
    dossie = {
        "nome_do_arquivo": os.path.basename(caminho_do_video),
        # REMOVEMOS: a detecção de objetos
        "textos_na_tela": textos,
        "descricao_visual_cenas": analise_visual.get("descricao_geral", ""),
        "score_nudez": score_nudez,
        "transcricao_audio": transcricao,
        "eh_menor_detectado_deepface": eh_menor,
        "resumo_facial_deepface": resumo_facial,
    }
    
    print(f"DOSSIÊ COMPLETO: {json.dumps(dossie, indent=2, ensure_ascii=False)}")
    
    resultado_final = julgamento_final_com_rag(dossie, models['retriever'])
    
    for frame in frames:
        if os.path.exists(frame):
            os.remove(frame)
            
    return resultado_final

def inicializar_modelos():
    """Carrega todos os modelos, forçando o uso de GPU."""
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"--- DETECTADO DISPOSITIVO: {device.upper()} ---")
    
    print("--- CARREGANDO MODELOS ---")
    
    MODELS['whisper'] = whisper.load_model("medium", device=device)
    MODELS['easyocr'] = easyocr.Reader(['pt', 'en'], gpu=(device=="cuda"))
    MODELS['nudenet'] = NudeClassifier()
    # REMOVEMOS: MODELS['yolo'] = YOLO('yolov8l.pt')
    
    MODELS['embeddings'] = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2", model_kwargs={'device': device})
    
    if not os.path.exists(VECTORSTORE_PATH):
        raise FileNotFoundError(f"Vectorstore não encontrado em {VECTORSTORE_PATH}.")
    
    MODELS['vectorstore'] = FAISS.load_local(VECTORSTORE_PATH, MODELS['embeddings'], allow_dangerous_deserialization=True)
    MODELS['retriever'] = MODELS['vectorstore'].as_retriever(search_kwargs={"k": 7})

    print("--- MODELOS DE BASE CARREGADOS. ---")

# --- O RESTANTE DO CÓDIGO (LIFESPAN, JULGAMENTO, ETC) ---
# ... (Cole aqui o resto do seu código da versão 5.0, que já está correto)
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Lifespan: Agendando a inicialização dos modelos...")
    await asyncio.to_thread(inicializar_modelos)
    print("Lifespan: Modelos inicializados, aplicação pronta.")
    yield
    print("Lifespan: Evento de finalização...")
    MODELS.clear()

app = FastAPI(lifespan=lifespan)

# (Funções de análise individuais que não mudaram)
def leitura_de_texto_easyocr(lista_de_frames, reader_easyocr):
    print("Analisando frames com EasyOCR...")
    textos_encontrados = set()
    for frame_path in lista_de_frames:
        results = reader_easyocr.readtext(frame_path)
        for (_, text, prob) in results:
            if prob > 0.4:
                textos_encontrados.add(text)
    texto_final = " ".join(textos_encontrados)
    print(f"Texto na tela: '{texto_final}'")
    return texto_final

def deteccao_nudez_nudenet(lista_de_frames, classifier_nudenet):
    print("Analisando frames com NudeNet...")
    if not lista_de_frames: return 0.0
    maior_pontuacao_unsafe = 0.0
    results = classifier_nudenet.classify(lista_de_frames)
    for _, result_dict in results.items():
        pontuacao_unsafe = result_dict.get('unsafe', 0.0)
        if pontuacao_unsafe > maior_pontuacao_unsafe:
            maior_pontuacao_unsafe = pontuacao_unsafe
    print(f"Maior pontuação de nudez: {maior_pontuacao_unsafe:.2f}")
    return maior_pontuacao_unsafe

def analise_facial_deepface(lista_de_frames):
    print("Analisando faces com DeepFace...")
    try:
        from deepface import DeepFace
    except ImportError:
        return False, "DeepFace não instalado."
    resumos_faciais = []
    idade_minima = 99
    for frame in lista_de_frames[:10]:
        try:
            resultados = DeepFace.analyze(img_path=frame, actions=['age'], enforce_detection=False)
            for rosto in resultados:
                idade = rosto['age']
                resumos_faciais.append(f"Rosto (idade ~{idade})")
                if idade < idade_minima:
                    idade_minima = idade
        except:
            pass
    if not resumos_faciais:
        return False, "Nenhum rosto detectado."
    resumo_final = f"Idade mínima ~{idade_minima}. Detalhes: " + " | ".join(list(set(resumos_faciais)))
    print(f"Resumo da Análise Facial: {resumo_final}")
    return idade_minima < 18, resumo_final

def transcricao_de_audio_whisper(video_path, model_whisper):
    print("Transcrevendo áudio com Whisper...")
    try:
        transcricao = model_whisper.transcribe(video_path, fp16=True)["text"]
        print(f"Transcrição: '{transcricao}'")
        return transcricao.strip()
    except Exception as e:
        print(f"Erro na transcrição: {e}")
        return ""

def julgamento_final_com_rag(dossie_completo, retriever):
    print("Iniciando julgamento final com RAG...")
    query_para_retriever = f"""- Descrições das Cenas do Vídeo: {dossie_completo.get('descricao_visual_cenas')}\n- Análise facial (DeepFace): {dossie_completo.get('resumo_facial_deepface')}\n- Transcrição do áudio: {dossie_completo.get('transcricao_audio')}\n- Texto na tela: {dossie_completo.get('textos_na_tela')}"""
    docs = retriever.get_relevant_documents(query_para_retriever)
    politicas_relevantes = "\n\n---\n\n".join([doc.page_content for doc in docs])
    prompt_final = f"""Você é um juiz de moderação. Analise as 'EVIDÊNCIAS DO VÍDEO' e determine se alguma das 'POLÍTICAS' foi violada. A 'Descrição das Cenas' é sua principal fonte de verdade. Se a descrição mencionar 'menor', 'adolescente', 'criança', ou indicativo de juventude, considere como presença de menor, mesmo que a 'Análise facial' diga o contrário. Sua resposta deve ser **APENAS UM OBJETO JSON**. Formato Violação: {{"policy_name": "Nome", "policy_priority": 0, "reason": "Justificativa."}}. Formato Allow: {{"policy_name": "Allow", "policy_priority": 99, "reason": "Nenhuma violação."}}"""
    try:
        response = ollama.generate(model='qwen2:7b', prompt=prompt_final, format='json', stream=False, options={"temperature": 0.0})
        response_text = response['response']
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            resultado_json = json.loads(json_str)
        else:
            raise ValueError("Nenhum JSON encontrado na resposta")
        print(f"Decisão da IA: {resultado_json}")
        return resultado_json
    except Exception as e:
        print(f"ERRO CRÍTICO no julgamento do LLM: {e}")
        return {"policy_name": "Analysis Failed", "policy_priority": -1, "reason": str(e)}

class VideoRequest(BaseModel):
    caminho_do_video: str

@app.post("/analisar_video/")
async def analisar_video_endpoint(request: VideoRequest):
    if not MODELS:
        print("AVISO: Modelos não estavam inicializados. Carregando sob demanda.")
        inicializar_modelos()
    resultado = analisar_video_localmente(request.caminho_do_video, MODELS)
    return resultado

if __name__ == "__main__":
    print("Iniciando o servidor de análise...")
    uvicorn.run(app, host="0.0.0.0", port=8000)