# Arquivo: backend/testador_local.py (Versão para processar múltiplos vídeos)
from main import analisar_video_localmente # Importa nossa função
import os
import json

# --- Configuração do Teste ---
PASTA_DE_VIDEOS = os.path.join("backend", "videos_para_teste")
TIPOS_DE_VIDEO = ('.mp4', '.mov', '.avi', '.mkv') # Adicione outras extensões se precisar

# --- Execução do Teste em Lote ---
if __name__ == "__main__":
    print("--- INICIANDO TESTE DO BACKEND EM LOTE ---")
    
    if not os.path.isdir(PASTA_DE_VIDEOS):
        print(f"Erro: A pasta de testes '{PASTA_DE_VIDEOS}' não foi encontrada.")
        exit()
        
    # Encontra todos os arquivos de vídeo na pasta
    lista_de_videos = [f for f in os.listdir(PASTA_DE_VIDEOS) if f.endswith(TIPOS_DE_VIDEO)]
    
    if not lista_de_videos:
        print(f"Nenhum vídeo encontrado na pasta '{PASTA_DE_VIDEOS}'.")
        exit()
        
    print(f"Encontrados {len(lista_de_videos)} vídeos para processar.")
    print("-" * 40)

    # Loop para processar cada vídeo
    for i, nome_do_video in enumerate(lista_de_videos):
        print(f"PROCESSANDO VÍDEO {i+1}/{len(lista_de_videos)}: {nome_do_video}")
        caminho_completo = os.path.join(PASTA_DE_VIDEOS, nome_do_video)
        
        # Chama a função de análise com o caminho do vídeo atual
        resultado_da_analise = analisar_video_localmente(caminho_completo)
        
        # Imprime o resultado de forma organizada
        print(f"\n--- RESULTADO PARA: {nome_do_video} ---")
        print(json.dumps(resultado_da_analise, indent=2, ensure_ascii=False))
        print("-" * 40)
        
    print("--- TODOS OS VÍDEOS FORAM PROCESSADOS ---")