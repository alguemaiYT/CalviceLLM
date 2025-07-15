import os
from openai import OpenAI

# --- Configuração ---
# A chave da API é lida da variável de ambiente XAI_API_KEY.
# Certifique-se de definir esta variável no seu ambiente.
# Ex: export XAI_API_KEY="sua_chave_aqui"
api_key = os.environ.get("XAI_API_KEY")

if not api_key:
    raise ValueError("A variável de ambiente XAI_API_KEY não foi definida.")

# Cliente da API OpenAI configurado para usar a API do Grok
client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1",
)

# --- Parâmetros da Requisição ---

# Mensagens a serem enviadas para a API.
# O formato é uma lista de dicionários, cada um com 'role' e 'content'.
# 'role' pode ser 'system', 'user', ou 'assistant'.
messages = [
    {"role": "system", "content": "Você é um assistente prestativo."},
    {"role": "user", "content": "Qual é a sua função?"},
]

# O modelo a ser usado para a geração da resposta.
model_name = "grok-1"

# Controle da aleatoriedade da resposta. Valores mais altos (ex: 0.8)
# tornam a resposta mais criativa, enquanto valores mais baixos (ex: 0.2)
# a tornam mais determinística.
temperature = 0.7

# Número máximo de tokens a serem gerados na resposta.
max_tokens = 1024

# Amostragem de núcleo. Apenas os tokens com probabilidade acumulada
# acima de 'top_p' são considerados. Ajuda a evitar respostas repetitivas.
top_p = 1.0

# Sequências de parada. A geração da resposta será interrompida se
# uma dessas sequências for encontrada.
stop_sequences = None

# Se True, a resposta será transmitida em tempo real (streaming).
stream = False

# --- Chamada da API ---

try:
    print("Enviando requisição para a API do Grok...")

    chat_completion = client.chat.completions.create(
        messages=messages,
        model=model_name,
        temperature=temperature,
        max_tokens=max_tokens,
        top_p=top_p,
        stop=stop_sequences,
        stream=stream,
        # --- Parâmetros Adicionais (opcional) ---
        # tools=[...],          # Para chamadas de função (function calling)
        # tool_choice="auto",   # Controle do uso de ferramentas
        # user="user-1234",     # ID do usuário para monitoramento
        # metadata={...},       # Metadados da requisição
    )

    # --- Processamento da Resposta ---

    if not stream:
        response_content = chat_completion.choices[0].message.content
        print("\n--- Resposta do Grok ---")
        print(response_content)
        print("\n----------------------")

except Exception as e:
    print(f"Ocorreu um erro: {e}")
