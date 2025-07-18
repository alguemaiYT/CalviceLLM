import asyncio
import os
import time
import aiohttp
import json

API_KEY = os.environ.get("XAI_API_KEY", "xai-rnG85Y2EC2qughTtzAWkQRyOrLJeC5N4ppOCVolCUovKL2xdYbR4XaiVeI9D9Kr0QEj6YVFpXYnJHGwb")
BASE_URL = "https://api.x.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Connection": "keep-alive"
}

# Mensagens mínimas
messages = [
    {"role": "system", "content": "Você é um assistente prestativo."},
    {"role": "user", "content": "Diga olá para mim."},
]

payload = {
    "model": "grok-3",
    "messages": messages,
    "temperature": 0.5,
    "max_tokens": 100,
    "top_p": 1.0,
    "stream": False
}

async def fetch_response(session):
    start = time.time()
    async with session.post(BASE_URL, headers=HEADERS, json=payload) as resp:
        resp.raise_for_status()
        data = await resp.json()
        latency = time.time() - start
        resposta = data["choices"][0]["message"]["content"]
        print(f"\n🧠 Resposta:\n{resposta}")
        print(f"\n⏱️ Latência total: {latency:.2f} segundos")

async def main():
    conn = aiohttp.TCPConnector(limit=1, force_close=False, keepalive_timeout=30)
    async with aiohttp.ClientSession(connector=conn) as session:
        await fetch_response(session)

if __name__ == "__main__":
    asyncio.run(main())
