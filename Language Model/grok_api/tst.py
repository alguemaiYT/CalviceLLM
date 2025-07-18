#!/usr/bin/env python3
import os
import asyncio
import time
gc_enabled = True
import gc
import uvloop
import aiohttp
import orjson
from asyncio import StreamReader, StreamWriter

# Desativa o GC em seções críticas para evitar pausas

def disable_gc():
    global gc_enabled
    if gc_enabled:
        gc.disable()
        gc_enabled = False

def enable_gc():
    global gc_enabled
    if not gc_enabled:
        gc.enable()
        gc_enabled = True

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

SOCKET_PATH = "/tmp/grok_daemon.sock"
API_KEY = os.getenv("XAI_API_KEY", "xai-...")
URL = "https://api.x.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip"
}
TIMEOUT = aiohttp.ClientTimeout(total=10)
SEMA = asyncio.Semaphore(1)
MAX_RETRIES = 3
BACKOFF_BASE = 0.5  # segundos

async def grok_request(session, text: str) -> tuple[str, float]:
    async with SEMA:
        disable_gc()
        for attempt in range(1, MAX_RETRIES + 1):
            start = time.time()
            try:
                async with session.post(
                    URL,
                    json={
                        "model": "grok-3-fast-latest",
                        "messages": [
                            {"role": "system", "content": "Você é um assistente prestativo. Responda em uma linha."},
                            {"role": "user", "content": text}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 256,
                        "top_p": 1.0,
                        "stream": False
                    }
                ) as r:
                    r.raise_for_status()
                    raw = await r.read()  # streaming chunked read
                latency = time.time() - start
                data = orjson.loads(raw)
                enable_gc()
                return data["choices"][0]["message"]["content"].strip(), latency

            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                if attempt == MAX_RETRIES:
                    enable_gc()
                    raise
                await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))
        enable_gc()

async def handle_client(reader: StreamReader, writer: StreamWriter, session: aiohttp.ClientSession):
    data = await reader.read(8192)
    msg = data.decode().strip()
    if not msg:
        writer.write(b"[ERRO] mensagem vazia\n")
        await writer.drain()
        writer.close()
        return

    try:
        resp, lat = await grok_request(session, msg)
        out = f"{resp}\n⏱️ {lat:.2f}s\n"
    except Exception as e:
        out = f"[ERRO] {e}\n"

    writer.write(out.encode())
    await writer.drain()
    writer.close()

async def main():
    if os.path.exists(SOCKET_PATH):
        os.remove(SOCKET_PATH)

    conn = aiohttp.TCPConnector(limit_per_host=1, keepalive_timeout=30)
    async with aiohttp.ClientSession(headers=HEADERS, connector=conn, timeout=TIMEOUT) as session:
        server = await asyncio.start_unix_server(
            lambda r, w: handle_client(r, w, session),
            path=SOCKET_PATH
        )
        print(f"🚀 Daemon rodando em {SOCKET_PATH}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
