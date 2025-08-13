# Arquivo: orquestrador.py (Rode este script no seu PC local)
import os
import requests
import time
import subprocess

# --- CONFIGURAÇÕES ---
# Cole aqui suas credenciais. NUNCA compartilhe sua chave de API!
RUNPOD_API_KEY = "rpa_MCUX6CIO4U04TP2HIIH6V1ILVLR4275ZP92KM5MGo42u7j"
POD_ID = "juwa7acfrg21y3" # ex: 'jwsctharf1qg2y'

# --- FUNÇÕES DA API DO RUNPOD ---

def controlar_pod(acao: str):
    """Envia um comando para a API do RunPod para 'start' ou 'stop'."""
    endpoint = f"https://api.runpod.io/v2/{POD_ID}/{'resume' if acao == 'start' else 'stop'}"
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    
    print(f"Enviando comando '{acao}' para o Pod {POD_ID}...")
    response = requests.post(endpoint, headers=headers)
    
    if response.status_code == 200:
        print(f"Comando '{acao}' enviado com sucesso.")
        return response.json()
    else:
        print(f"Erro ao enviar comando '{acao}': {response.status_code} - {response.text}")
        return None

def esperar_pod_ficar_pronto():
    """Verifica o status do Pod até que ele esteja 'RUNNING'."""
    endpoint = f"https://api.runpod.io/v2/{POD_ID}"
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    
    print("Aguardando o Pod ficar 100% pronto (pode levar alguns minutos)...")
    while True:
        try:
            response = requests.get(endpoint, headers=headers)
            if response.status_code == 200:
                status = response.json().get('desiredStatus')
                print(f"Status atual do Pod: {status}")
                if status == 'RUNNING':
                    print("Pod está 'RUNNING' e pronto para receber conexões!")
                    # Espera extra para garantir que os serviços internos subam
                    time.sleep(30) 
                    break
            else:
                print(f"Aguardando... status code: {response.status_code}")
            
            time.sleep(15) # Espera 15 segundos entre cada verificação
        except Exception as e:
            print(f"Erro ao verificar status: {e}")
            time.sleep(15)

# --- FLUXO PRINCIPAL DO ORQUESTRADOR ---

if __name__ == "__main__":
    try:
        # 1. Ligar o Pod
        controlar_pod('start')
        
        # 2. Esperar ele ficar pronto
        esperar_pod_ficar_pronto()
        
        # 3. Iniciar o servidor FastAPI no Pod (Lembre-se de fazer isso manualmente por enquanto)
        print("\n--- AÇÃO NECESSÁRIA ---")
        print("O Pod está no ar. Por favor, conecte-se a ele via SSH/Terminal e inicie o servidor com:")
        print("source venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000")
        input("Pressione Enter aqui quando o servidor estiver rodando no Pod...")
        
        # 4. Rodar o robô Playwright localmente
        print("\nIniciando o robô Playwright no seu PC...")
        # Garante que estamos no diretório certo para o Playwright
        caminho_automacao = os.path.join(os.path.dirname(__file__), 'automacao')
        subprocess.run(["npx", "playwright", "test", "--headed"], cwd=caminho_automacao, check=True)
        print("Robô Playwright finalizou o trabalho.")

    except Exception as e:
        print(f"Ocorreu um erro no orquestrador: {e}")
    finally:
        # 5. Desligar o Pod, não importa o que aconteça
        print("\nFinalizando a sessão...")
        controlar_pod('stop')