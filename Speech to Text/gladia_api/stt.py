import asyncio
import base64
import json
import signal
import sys
from datetime import time
from typing import Literal, TypedDict

import pyaudio
import requests
from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed

# Constantes
GLADIA_API_URL = "https://api.gladia.io"
P = pyaudio.PyAudio()
CHANNELS = 1
FORMAT = pyaudio.paInt16
FRAMES_PER_BUFFER = 3200
SAMPLE_RATE = 16000

# Flag global de parada
stop_already_called = False

# Tipagens
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

# Utilitários
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

# Receber mensagens do socket
async def print_messages_from_socket(socket: ClientConnection) -> None:
    async for message in socket:
        content = json.loads(message)

        if content["type"] == "transcript" and content["data"]["is_final"]:
            text = content["data"]["utterance"]["text"].strip()
            print(text)

        elif content["type"] == "post_final_transcript":
            summary = content["data"].get("summarization", {}).get("results")
            if summary:
                print(f"\n[Resumo]: {summary}")

# Encerramento controlado
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

# Envio de áudio
async def send_audio(socket: ClientConnection) -> None:
    stream = P.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=SAMPLE_RATE,
        input=True,
        frames_per_buffer=FRAMES_PER_BUFFER,
    )

    try:
        while True:
            try:
                data = stream.read(FRAMES_PER_BUFFER, exception_on_overflow=False)
            except OSError as e:
                if e.errno == -9988:  # Stream closed
                    break
                else:
                    raise

            data = base64.b64encode(data).decode("utf-8")
            json_data = json.dumps({"type": "audio_chunk", "data": {"chunk": data}})
            await socket.send(json_data)
            await asyncio.sleep(0.1)
    except ConnectionClosed:
        pass
    finally:
        stream.stop_stream()
        stream.close()

# Configuração do streaming
STREAMING_CONFIGURATION: StreamingConfiguration = {
    "encoding": "wav/pcm",
    "bit_depth": 16,
    "sample_rate": SAMPLE_RATE,
    "channels": CHANNELS,
    "model": "solaria-1",
    "endpointing": 0.05,
    "maximum_duration_without_endpointing": 5,
    "language_config": {
        "languages": ["pt"],
        "code_switching": False,
    },
    "pre_processing": {
        "audio_enhancer": True,
        "speech_threshold": 0.8,
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
        "translation_config": {
            "target_languages": ["en"],
            "model": "base",
            "match_original_utterances": True,
            "lipsync": True,
            "context_adaptation": True,
            "context": "<string>",
            "informal": False,
        },
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
        "receive_pre_processing_events": False,
        "receive_realtime_processing_events": False,
        "receive_post_processing_events": True,
        "receive_acknowledgments": False,
        "receive_errors": True,
        "receive_lifecycle_events": False,
    },
    "callback": False,
    "callback_config": {
        "url": "",
        "receive_final_transcripts": True,
        "receive_speech_events": False,
        "receive_pre_processing_events": False,
        "receive_realtime_processing_events": False,
        "receive_post_processing_events": False,
        "receive_acknowledgments": False,
        "receive_errors": False,
        "receive_lifecycle_events": False,
    },
}

# Main
async def main():
    response = init_live_session(STREAMING_CONFIGURATION)
    async with connect(response["url"]) as websocket:
        loop = asyncio.get_running_loop()
        loop.add_signal_handler(
            signal.SIGINT,
            lambda: loop.create_task(stop_recording(websocket)),
        )

        send_audio_task = asyncio.create_task(send_audio(websocket))
        print_messages_task = asyncio.create_task(print_messages_from_socket(websocket))
        await asyncio.wait([send_audio_task, print_messages_task])

# Execução
if __name__ == "__main__":
    asyncio.run(main())
