import os
import requests
import time
import subprocess

# --- CONFIGURAÇÕES ---
API_KEY = "rpa_MCUX6CIO4U04TP2HIIH6V1ILVLR4275ZP92KM5MGo42u7j"
POD_ID = "rhr2d843z3ju3r"

# --- FUNÇÕES DA API DO RUNPOD (GraphQL) ---

def controlar_pod_graphql(acao: str):
    """Envia um comando para a API do RunPod usando GraphQL."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    if acao == 'start':
        mutation = f"""
        mutation {{
          podResume(input: {{ podId: "{POD_ID}" }}) {{
            id
            desiredStatus
          }}
        }}
        """
    else:  # stop
        mutation = f"""
        mutation {{
          podStop(input: {{ podId: "{POD_ID}" }}) {{
            id
            desiredStatus
          }}
        }}
        """
    
    print(f"Enviando comando '{acao}' para o Pod {POD_ID}...")
    response = requests.post(
        "https://api.runpod.io/graphql",
        json={"query": mutation},
        headers=headers
    )
    
    if response.status_code == 200:
        print(f"Comando '{acao}' enviado com sucesso.")
        return response.json()
    else:
        print(f"Erro ao enviar comando '{acao}': {response.status_code} - {response.text}")
        return None

def verificar_status_pod_graphql():
    """Verifica o status do Pod usando GraphQL."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    
    query = f"""
    {{
      pod(input: {{ podId: "{POD_ID}" }}) {{
        id
        desiredStatus
        runtime {{
          uptimeSeconds
          publicIp
          ports {{
            privatePort
            publicPort
          }}
        }}
      }}
    }}
    """
    
    response = requests.post(
        "https://api.runpod.io/graphql",
        json={"query": query},
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        pod = data.get('data', {}).get('pod')
        if pod:
            return pod.get('desiredStatus')
    return None

# --- FLUXO PRINCIPAL ---

if __name__ == "__main__":
    try:
        # 1. Verificar status atual
        status = verificar_status_pod_graphql()
        print(f"Status atual do pod: {status}")
        
        if status != "RUNNING":
            # 2. Ligar o Pod se não estiver rodando
            controlar_pod_graphql('start')
            
            # 3. Esperar ficar pronto
            print("Aguardando o Pod ficar pronto...")
            while True:
                status = verificar_status_pod_graphql()
                if status == "RUNNING":
                    print("Pod está RUNNING!")
                    time.sleep(30)  # Espera extra
                    break
                time.sleep(15)
        
        # 4. Instruções para conectar
        print("\n--- AÇÃO NECESSÁRIA ---")
        print("Conecte ao pod usando:")
        print("ssh root@47.47.180.59 -p 21726 -i /storage/moderador-IA/Moderador-IA")
        print("\nDepois inicie o servidor com:")
        print("cd /workspace/Moderador-IA && source /workspace/venv/bin/activate && uvicorn backend.main:app --host 0.0.0.0 --port 8000")
        input("\nPressione Enter quando o servidor estiver rodando...")
        
        # 5. Rodar o Playwright
        print("\nIniciando o robô Playwright...")
        caminho_automacao = os.path.join(os.path.dirname(__file__), 'automacao')
        subprocess.run(["npx", "playwright", "test", "--headed"], cwd=caminho_automacao, check=True)
        
    except Exception as e:
        print(f"Erro: {e}")
    finally:
        print("\nTrabalho concluído!")