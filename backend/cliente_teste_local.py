import requests # Lembre-se de instalar: pip install requests
import os
import json

# --- Configuração do Cliente ---
PASTA_DE_VIDEOS = os.path.join("backend", "videos_para_teste")
TIPOS_DE_VIDEO = ('.mp4', '.mov', '.avi', '.mkv')
URL_DO_SERVIDOR = "http://127.0.0.1:8000/analisar_video/"

def testar_servidor():
    print("--- INICIANDO CLIENTE DE TESTE EM LOTE ---")
    
    if not os.path.isdir(PASTA_DE_VIDEOS):
        print(f"Erro: A pasta de testes '{PASTA_DE_VIDEOS}' não foi encontrada.")
        return
        
    lista_de_videos = [f for f in os.listdir(PASTA_DE_VIDEOS) if f.endswith(TIPOS_DE_VIDEO)]
    
    if not lista_de_videos:
        print(f"Nenhum vídeo encontrado na pasta '{PASTA_DE_VIDEOS}'.")
        return
        
    print(f"Encontrados {len(lista_de_videos)} vídeos para enviar para análise.")
    print("-" * 40)
    
    for nome_do_video in lista_de_videos:
        caminho_completo = os.path.join(PASTA_DE_VIDEOS, nome_do_video)
        
        print(f"--> Enviando {nome_do_video} para o servidor...")
        
        try:
            # Monta o corpo da requisição com o caminho do vídeo
            payload = {"caminho_do_video": caminho_completo}
            
            # Envia a requisição POST para o servidor
            response = requests.post(URL_DO_SERVIDOR, json=payload)
            
            if response.status_code == 200:
                resultado = response.json()
                print(f"<-- Resultado para {nome_do_video}:")
                print(json.dumps(resultado, indent=2, ensure_ascii=False))
            else:
                print(f"ERRO do servidor para {nome_do_video}: Status {response.status_code}, Resposta: {response.text}")
                
        except requests.exceptions.ConnectionError:
            print("\nERRO FATAL: Não foi possível conectar ao servidor.")
            print(f"Verifique se o servidor ('python backend/main.py') está rodando no outro terminal.")
            return # Aborta o script se não conseguir conectar
        except Exception as e:
            print(f"ERRO INESPERADO ao processar {nome_do_video}: {repr(e)}")
            
        print("-" * 40)
        
    print("--- TODOS OS VÍDEOS FORAM PROCESSADOS ---")

if __name__ == "__main__":
    testar_servidor()