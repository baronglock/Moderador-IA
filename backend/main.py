# Arquivo: backend/main.py (Versão Final e Completa para Servidor com GPU)
import os
import json
import whisper
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, HttpUrl
import cv2
from ultralytics import YOLO
import easyocr
from operator import itemgetter
import ollama
import numpy as np
import soundfile as sf
import librosa

# Importações para Análise de Som e Nudez
from panns_inference import AudioTagging
from nudenet import NudeClassifier

# Importações do Langchain
from langchain_community.document_loaders import TextLoader
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import CharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# --- Constantes ---
POLITICAS_PATH = os.path.join("backend", "politicas", "politicas.md")
VECTORSTORE_PATH = os.path.join("backend", "faiss_index")

# --- FUNÇÕES DE ANÁLISE DE ALTA PRECISÃO ---

def extrair_frames(video_path, num_frames=5):
    print(f"Extraindo até {num_frames} frames do vídeo...")
    if not os.path.exists(video_path): return []
    cap = cv2.VideoCapture(video_path)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames < 1: return []
    intervalo = total_frames // num_frames if num_frames > 0 and total_frames > num_frames else 1
    caminhos_frames = []
    pasta_temp = os.path.join("backend", "temp_frames")
    os.makedirs(pasta_temp, exist_ok=True)
    for i in range(num_frames):
        frame_id = i * intervalo
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_id)
        ret, frame = cap.read()
        if not ret: continue
        frame_path = os.path.join(pasta_temp, f"frame_{i}.jpg")
        cv2.imwrite(frame_path, frame)
        caminhos_frames.append(frame_path)
    cap.release()
    print(f"{len(caminhos_frames)} frames extraídos com sucesso.")
    return caminhos_frames

def analisar_frames_objetos_preciso(lista_de_frames):
    print("Analisando frames com YOLOv8-Large...")
    model = YOLO('yolov8l.pt')
    objetos_detectados = set()
    for frame_path in lista_de_frames:
        results = model(frame_path, verbose=False)
        for result in results:
            for box in result.boxes:
                if box.conf[0] > 0.4:
                    nome_objeto = result.names[int(box.cls[0])]
                    objetos_detectados.add(nome_objeto)
    print("Objetos detectados (alta precisão):", list(objetos_detectados))
    return list(objetos_detectados)

def analisar_frames_ocr(lista_de_frames):
    print("Analisando frames com EasyOCR (GPU)...")
    reader = easyocr.Reader(['pt', 'en'], gpu=True)
    textos_encontrados = set()
    for frame_path in lista_de_frames:
        results = reader.readtext(frame_path)
        for (bbox, text, prob) in results:
            if prob > 0.5:
                textos_encontrados.add(text)
    texto_final = " ".join(textos_encontrados)
    print("Texto encontrado na tela:", texto_final)
    return texto_final

def analisar_frames_nudez(lista_de_frames):
    print("Analisando frames com NudeNet para detecção de nudez...")
    classifier = NudeClassifier()
    maior_pontuacao_unsafe = 0.0
    results = classifier.classify(lista_de_frames)
    for frame_path, result_dict in results.items():
        pontuacao_unsafe = result_dict.get('unsafe', 0.0)
        if pontuacao_unsafe > maior_pontuacao_unsafe:
            maior_pontuacao_unsafe = pontuacao_unsafe
    print(f"Maior pontuação de nudez (unsafe) encontrada: {maior_pontuacao_unsafe:.2f}")
    return maior_pontuacao_unsafe

def inspecao_visual_avancada_vlm(lista_de_frames):
    print("Iniciando inspeção visual avançada com LLaVA...")
    if not lista_de_frames: return {"flags_visuais": [], "descricao_geral": "Nenhuma imagem para descrever."}
    frame_central = lista_de_frames[len(lista_de_frames) // 2]
    flags_visuais = []
    descricao_geral = "N/A"
    try:
        res_desc = ollama.chat(model='qwen2:7b', messages=[{'role': 'user', 'content': 'Descreva a ação principal nesta imagem em uma frase curta.', 'images': [frame_central]}])
        descricao_geral = res_desc['message']['content']
        # Adicione aqui outras perguntas específicas se necessário (gestos, símbolos, etc.)
    except Exception as e:
        descricao_geral = f"Erro na descrição VLM: {e}"
    print(f"Inspeção VLM concluída. Descrição: '{descricao_geral}'. Flags: {flags_visuais}")
    return {"flags_visuais": flags_visuais, "descricao_geral": descricao_geral}

def analisar_eventos_de_som(audio_path):
    print("Analisando eventos de som com PANNs...")
    try:
        at = AudioTagging(checkpoint_path=None, device='cuda') 
        audio, _ = librosa.core.load(audio_path, sr=32000, mono=True)
        audio = audio[None, :]
        _, embedding = at.inference(audio)
        framewise_output = embedding['framewise_output']
        sorted_indexes = np.argsort(np.max(framewise_output, axis=0))[::-1]
        eventos = [at.labels[sorted_indexes[i]] for i in range(5)]
        print("Eventos de som detectados:", eventos)
        return eventos
    except Exception as e:
        print(f"Erro na análise de som: {e}")
        return ["N/A"]

# --- Funções do Motor RAG ---

def carregar_e_criar_vetores():
    loader = TextLoader(POLITICAS_PATH)
    documents = loader.load()
    text_splitter = CharacterTextSplitter(chunk_size=1500, chunk_overlap=100)
    docs = text_splitter.split_documents(documents)
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = FAISS.from_documents(docs, embeddings)
    db.save_local(VECTORSTORE_PATH)
    return db

def get_chain():
    if not os.path.exists(VECTORSTORE_PATH):
        vectorstore = carregar_e_criar_vetores()
    else:
        embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        vectorstore = FAISS.load_local(VECTORSTORE_PATH, embeddings, allow_dangerous_deserialization=True)

    retriever = vectorstore.as_retriever()
    template = """
    Você é um moderador de conteúdo de IA. Sua tarefa é analisar um dossiê completo de dados de um vídeo e identificar a violação mais grave com base ESTRITAMENTE nas políticas fornecidas.
    As políticas são hierárquicas por Prioridade (P0 > P1 > P2...).

    POLÍTICAS DE MODERAÇÃO RELEVANTES:
    {context}

    DADOS EXTRAÍDOS DO VÍDEO (Dossiê):
    {input_data}

    SIGA ESTES PASSOS DE RACIOCÍNIO:
    1.  **Análise de Contexto:** Analise a combinação de todos os dados do dossiê para entender o que está acontecendo no vídeo.
    2.  **Identificação de Violações:** Com base no contexto, liste TODAS as políticas-mãe (ex: 'Safety Recheck') que foram violadas.
    3.  **Seleção por Prioridade:** Se múltiplas políticas forem violadas, escolha a que tiver a MAIOR prioridade (P0 vence P1, etc.).

    FORNEÇA A SAÍDA APENAS EM FORMATO JSON VÁLIDO, contendo a `policy_name`, a `policy_priority`, e uma `reason`.

    JSON de Saída:
    """
    prompt = PromptTemplate.from_template(template)
    llm = ollama.Client()

    chain = (
        {
            "context": itemgetter("combined_input") | retriever,
            "input_data": itemgetter("combined_input"),
        }
        | prompt
        | (lambda x: llm.chat(model='llama3:8b', messages=[{'role': 'user', 'content': x.text}])['message']['content'])
        | StrOutputParser()
    )
    return chain

# --- FUNÇÃO PRINCIPAL DE ANÁLISE (COMPLETA) ---
def analisar_video_localmente(video_path: str):
    if not os.path.exists(video_path):
        return {"erro": "Arquivo de vídeo não encontrado!"}

    # Análise Visual Completa
    frames = extrair_frames(video_path)
    objetos_detectados = analisar_frames_objetos_preciso(frames)
    texto_na_tela = analisar_frames_ocr(frames)
    inspecao_vlm = inspecao_visual_avancada_vlm(frames)
    pontuacao_nudez = analisar_frames_nudez(frames)
    
    # Análise de Áudio Completa
    print("Carregando modelo Whisper (Medium)...")
    model_whisper = whisper.load_model("medium")
    transcricao_texto = model_whisper.transcribe(video_path, fp16=True)["text"]
    print("Transcrição concluída:", transcricao_texto)
    eventos_de_som = analisar_eventos_de_som(video_path)

    # Monta o dossiê final completo em formato de string
    dossie_completo_str = f"""
    - Transcrição do Áudio: "{transcricao_texto if transcricao_texto.strip() else 'Áudio vazio.'}"
    - Eventos de Som Detectados: {eventos_de_som}
    - Objetos Visuais Detectados: {objetos_detectados}
    - Texto na Tela (OCR): "{texto_na_tela if texto_na_tela.strip() else 'Nenhum texto encontrado.'}"
    - Descrição da Ação (IA Visual): "{inspecao_vlm['descricao_geral']}"
    - Flags Visuais de Alerta (IA Visual): {inspecao_vlm['flags_visuais']}
    - Pontuação de Nudez (0.0 a 1.0): {pontuacao_nudez:.2f}
    """
    print("\n--- DOSSIÊ COMPLETO ENVIADO PARA JULGAMENTO ---")
    print(dossie_completo_str)
    print("---------------------------------------------\n")

    # Inicia o julgamento final com o motor RAG
    print("Iniciando julgamento final com o motor RAG...")
    chain = get_chain()
    resultado_rag_str = chain.invoke({"combined_input": dossie_completo_str})
    
    # Tenta extrair o JSON da resposta do LLM
    try:
        json_start = resultado_rag_str.find('{')
        json_end = resultado_rag_str.rfind('}') + 1
        if json_start != -1 and json_end != 0:
            json_str = resultado_rag_str[json_start:json_end]
            return json.loads(json_str)
        else:
            raise json.JSONDecodeError("JSON não encontrado", resultado_rag_str, 0)
    except json.JSONDecodeError:
        return {"erro": "Saída inválida do LLM", "output_text": resultado_rag_str}

# --- Configuração do App FastAPI ---
app = FastAPI()
class VideoRequest(BaseModel):
    video_url: str # Mudado de HttpUrl para str para mais flexibilidade
@app.post("/analisar_video/")
async def analisar_video_endpoint(request: VideoRequest):
    # No futuro, esta função fará o download do vídeo da URL e chamará a análise.
    print(f"Recebida requisição para analisar a URL: {request.video_url}")
    # A implementação real do download e chamada da análise iria aqui.
    return {"status": "Endpoint online, pronto para implementação."}

if __name__ == "__main__":
    # Esta parte só é usada para rodar o servidor, não afeta o testador_local.py
    uvicorn.run(app, host="127.0.0.1", port=8000)