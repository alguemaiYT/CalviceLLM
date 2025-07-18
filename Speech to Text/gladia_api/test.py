import asyncio
import base64
import json
import signal
import subprocess
import sys
import time as t
from datetime import time
from typing import Literal, TypedDict

import pyaudio
import requests
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

GLADIA_API_URL = "https://api.gladia.io"
P = pyaudio.PyAudio()
CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 3200
SAMPLE_RATE = 16000

stop_already_called = False

class InitiateResponse(TypedDict):
    id: str
    url: str

class LanguageConfiguration(TypedDict):
    languages: list[str] | None
    code_switching: bool | None

class VocabularyEntry(TypedDict, total=False):
    value: str
    pronunciations: list[str]
    intensity: float
    language: str

class CustomVocabularyConfig(TypedDict):
    vocabulary: list[str | VocabularyEntry]
    default_intensity: float

class CustomSpellingConfig(TypedDict):
    spelling_dictionary: dict[str, list[str]]

class StreamingConfiguration(TypedDict):
    encoding: Literal["wav/pcm", "wav/alaw", "wav/ulaw"]
    bit_depth: Literal[8, 16, 24, 32]
    sample_rate: Literal[8000, 16000, 32000, 44100, 48000]
    channels: int
    model: str
    endpointing: float
    maximum_duration_without_endpointing: int
    language_config: LanguageConfiguration | None
    pre_processing: dict[str, bool | float]
    realtime_processing: dict[str, bool | dict]
    post_processing: dict[str, bool | dict]
    messages_config: dict[str, bool]
    callback: bool
    callback_config: dict[str, bool | str]

def get_gladia_key() -> str:
    if len(sys.argv) != 2 or not sys.argv[1]:
        print("Você deve fornecer a chave da Gladia como argumento.")
        exit(1)
    return sys.argv[1]

def init_live_session(config: StreamingConfiguration) -> InitiateResponse:
    gladia_key = get_gladia_key()
    response = requests.post(
        f"{GLADIA_API_URL}/v2/live",
        headers={"X-Gladia-Key": gladia_key},
        json=config,
        timeout=3,
    )
    if not response.ok:
        print(f"{response.status_code}: {response.text or response.reason}")
        exit(response.status_code)
    return response.json()

def format_duration(seconds: float) -> str:
    milliseconds = int(seconds * 1_000)
    return time(
        hour=milliseconds // 3_600_000,
        minute=(milliseconds // 60_000) % 60,
        second=(milliseconds // 1_000) % 60,
        microsecond=milliseconds % 1_000 * 1_000,
    ).isoformat(timespec="milliseconds")

async def stop_recording(websocket: ClientConnection) -> None:
    global stop_already_called
    if stop_already_called:
        return
    stop_already_called = True

    try:
        await websocket.send(json.dumps({"type": "stop_recording"}))
        await asyncio.sleep(0)
    except ConnectionClosed:
        pass
    finally:
        P.terminate()

async def print_messages_from_socket(socket: ClientConnection, stop_event: asyncio.Event) -> None:
    transcription = ""
    summary = ""

    async for message in socket:
        content = json.loads(message)

        if content["type"] == "transcript" and content["data"]["is_final"]:
            transcription = content["data"]["utterance"]["text"].strip()
            print(f"\nPergunta: {transcription}")
            stop_event.set()
            await stop_recording(socket)  # <<< PARA O ÁUDIO IMEDIATAMENTE

        elif content["type"] == "post_final_transcript":
            data = content["data"]
            transcription = data.get("transcription", {}).get("full_transcript", "").strip()
            summary = data.get("summarization", {}).get("results", "")

            if summary:
                print(f"[Resumo]: {summary}")

            if transcription:
                start = t.time()
                try:
                    result = subprocess.run(
                        ["/root/testplace/LLM/pergunta.sh", transcription, summary],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    resposta = result.stdout.strip()
                    elapsed = round(t.time() - start, 2)
                    print(f"Resposta: {resposta} ⏱️ {elapsed}s\n")
                except Exception as e:
                    print(f"[Erro ao executar pergunta.sh]: {e}")
                break  # encerra loop após resposta final

async def send_audio(socket: ClientConnection, stop_event: asyncio.Event) -> None:
    stream = P.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER,
    )

    try:
        while not stop_event.is_set():
            data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
            encoded = base64.b64encode(data).decode("utf-8")
            await socket.send(json.dumps({"type": "audio_chunk", "data": {"chunk": encoded}}))
            await asyncio.sleep(0.1)
    except Exception as e:
        print(f"[Erro no envio de áudio]: {e}")
    finally:
        stream.stop_stream()
        stream.close()

STREAMING_CONFIGURATION: StreamingConfiguration = {
    "encoding": "wav/pcm",
    "bit_depth": 16,
    "sample_rate": SAMPLE_RATE,
    "channels": CHANNELS,
    "model": "solaria-1",
    "endpointing": 0.05,
    "maximum_duration_without_endpointing": 6,
    "language_config": {
        "languages": ["pt"],
        "code_switching": False,
    },
    "pre_processing": {
        "audio_enhancer": True,
        "speech_threshold": 0.6,
    },
    "realtime_processing": {
        "custom_vocabulary": False,
        "custom_vocabulary_config": {
            "vocabulary": [],
            "default_intensity": 0.5,
        },
        "custom_spelling": False,
        "custom_spelling_config": {
            "spelling_dictionary": {},
        },
        "translation": False,
        "translation_config": {},
        "named_entity_recognition": False,
        "sentiment_analysis": False,
    },
    "post_processing": {
        "summarization": True,
        "summarization_config": {"type": "general"},
        "chapterization": False,
    },
    "messages_config": {
        "receive_final_transcripts": True,
        "receive_speech_events": False,
        "receive_post_processing_events": True,
        "receive_errors": True,
    },
    "callback": False,
    "callback_config": {},
}

async def main():
    response = init_live_session(STREAMING_CONFIGURATION)
    async with connect(response["url"]) as websocket:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(signal.SIGINT, lambda: loop.create_task(stop_recording(websocket)))

        stop_event = asyncio.Event()

        tasks = [
            asyncio.create_task(send_audio(websocket, stop_event)),
            asyncio.create_task(print_messages_from_socket(websocket, stop_event)),
        ]
        await asyncio.gather(*tasks)

        await stop_recording(websocket)
        sys.exit(0)

if __name__ == "__main__":
    asyncio.run(main())
