# Arquivo: backend/testador_local.py (Versão Corrigida e Otimizada)
from main import analisar_video_localmente, inicializar_modelos # IMPORTA A NOVA FUNÇÃO
import os
import json

# --- Configuração do Teste ---
PASTA_DE_VIDEOS = os.path.join("backend", "videos_para_teste")
TIPOS_DE_VIDEO = ('.mp4', '.mov', '.avi', '.mkv')

# --- Execução do Teste em Lote ---
if __name__ == "__main__":
    print("--- INICIANDO TESTE DO BACKEND EM LOTE ---")
    
    # PASSO 1: Carrega todos os modelos na memória ANTES de começar a processar.
    # Isso é feito apenas uma vez.
    try:
        modelos_carregados = inicializar_modelos()
    except Exception as e:
        print(f"ERRO FATAL: Não foi possível inicializar os modelos de IA. {e}")
        exit()

    if not os.path.isdir(PASTA_DE_VIDEOS):
        print(f"Erro: A pasta de testes '{PASTA_DE_VIDEOS}' não foi encontrada.")
        exit()
        
    lista_de_videos = [f for f in os.listdir(PASTA_DE_VIDEOS) if f.endswith(TIPOS_DE_VIDEO)]
    
    if not lista_de_videos:
        print(f"Nenhum vídeo encontrado na pasta '{PASTA_DE_VIDEOS}'.")
        exit()
        
    print(f"\nEncontrados {len(lista_de_videos)} vídeos para processar.")
    print("-" * 40)
    
    # Loop para processar cada vídeo
    for i, nome_do_video in enumerate(lista_de_videos):
        caminho_completo = os.path.join(PASTA_DE_VIDEOS, nome_do_video)
        
        try:
            # PASSO 2: Chama a função de análise passando os modelos já carregados.
            # Isso é super rápido, pois não há recarregamento.
            resultado_da_analise = analisar_video_localmente(caminho_completo, modelos_carregados)
            
            print(f"\n--- RESULTADO FINAL PARA: {nome_do_video} ---")
            print(json.dumps(resultado_da_analise, indent=2, ensure_ascii=False))
            print("-" * 40)
            
        except Exception as e:
            print(f"ERRO INESPERADO ao processar {nome_do_video}: {e}")
            print("-" * 40)
        
    print("--- TODOS OS VÍDEOS FORAM PROCESSADOS ---")