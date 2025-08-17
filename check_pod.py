python3 << 'EOF'
import requests

API_KEY = "rpa_MCUX6CIO4U04TP2HIIH6V1ILVLR4275ZP92KM5MGo42u7j"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Testa o endpoint mais básico
print("Testando conexão com a API RunPod...")
response = requests.get("https://api.runpod.io/v2/user", headers=headers)
print(f"Status: {response.status_code}")
print(f"Resposta: {response.text}")

# Tenta o endpoint graphql também
print("\nTestando endpoint GraphQL...")
query = {"query": "{ myself { id email } }"}
response = requests.post("https://api.runpod.io/graphql", json=query, headers=headers)
print(f"Status: {response.status_code}")
print(f"Resposta: {response.text}")
EOF