#!/usr/bin/env python3
import os
import asyncio
import time
import gc
import uvloop
import aiohttp
import orjson
import logging
from asyncio import StreamReader, StreamWriter
from collections import OrderedDict
from contextlib import contextmanager

asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

SOCKET_PATH = "/tmp/grok_daemon.sock"
API_KEY = os.getenv("XAI_API_KEY", "xai-rnG85Y2EC2qughTtzAWkQRyOrLJeC5N4ppOCVolCUovKL2xdYbR4XaiVeI9D9Kr0QEj6YVFpXYnJHGwb")
URL = "https://api.x.ai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept-Encoding": "gzip"
}
TIMEOUT = aiohttp.ClientTimeout(sock_connect=3, sock_read=7, total=10)
SEMA = asyncio.Semaphore(1)
MAX_RETRIES = 3
BACKOFF_BASE = 0.5  # segundos

CACHE_SIZE = 100
CACHE = OrderedDict()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("grok_daemon")

@contextmanager
def gc_disabled():
    gc_was_enabled = gc.isenabled()
    if gc_was_enabled:
        gc.disable()
    try:
        yield
    finally:
        if gc_was_enabled:
            gc.enable()

def cache_get(text: str):
    resp = CACHE.get(text)
    if resp:
        # Move para o fim (mais recente)
        CACHE.move_to_end(text)
    return resp

def cache_set(text: str, response: str):
    if len(CACHE) >= CACHE_SIZE:
        CACHE.popitem(last=False)
    CACHE[text] = response

async def grok_request(session, text: str) -> tuple[str, float]:
    cached = cache_get(text)
    if cached:
        return cached, 0.0

    async with SEMA:
        with gc_disabled():
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
                            "temperature": 0.25,
                            "max_tokens": 256,
                            "top_p": 1.0,
                            "stream": False
                        }
                    ) as r:
                        r.raise_for_status()
                        raw = await r.read()  # streaming chunked read
                    latency = time.time() - start
                    data = orjson.loads(raw)
                    content = data["choices"][0]["message"]["content"].strip()
                    cache_set(text, content)
                    return content, latency

                except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                    logger.warning(f"Erro na requisição (tentativa {attempt}): {e}")
                    if attempt == MAX_RETRIES:
                        raise
                    await asyncio.sleep(BACKOFF_BASE * (2 ** (attempt - 1)))

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

    connector = aiohttp.TCPConnector(limit_per_host=3, keepalive_timeout=30)
    async with aiohttp.ClientSession(headers=HEADERS, connector=connector, timeout=TIMEOUT) as session:
        server = await asyncio.start_unix_server(
            lambda r, w: handle_client(r, w, session),
            path=SOCKET_PATH
        )
        logger.info(f"🚀 Daemon rodando em {SOCKET_PATH}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())
