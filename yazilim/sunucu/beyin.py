#!/usr/bin/env python3
"""
Tepecan beyin sunucusu — ses->metin ve metin->ses.

Bu iki iş de maskotun içindeki Pi için ağır; buraya alındı. LLM ayrı bir
servis (Ollama) olarak aynı makinede çalışır, Pi ona doğrudan bağlanır.

    uvicorn beyin:app --host 0.0.0.0 --port 8000

Ortam değişkenleri:
    STT_MODEL=small        CPU'da makul, Türkçesi iyi (varsayılan)
    STT_DEVICE=cuda        GPU varsa
    PIPER_MODEL=/yol/tr_TR-dfki-medium.onnx
"""

import os
import subprocess
import tempfile

from fastapi import FastAPI, File, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from faster_whisper import WhisperModel

STT_MODEL = os.getenv("STT_MODEL", "small")
STT_DEVICE = os.getenv("STT_DEVICE", "cpu")
STT_COMPUTE = os.getenv("STT_COMPUTE", "int8" if STT_DEVICE == "cpu" else "float16")

PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_MODEL = os.getenv("PIPER_MODEL",
                        os.path.expanduser("~/piper/tr_TR-dfki-medium.onnx"))

print(f"faster-whisper yükleniyor: {STT_MODEL} ({STT_DEVICE}/{STT_COMPUTE})")
whisper = WhisperModel(STT_MODEL, device=STT_DEVICE, compute_type=STT_COMPUTE)
print("Hazır.")

app = FastAPI(title="Tepecan beyin")


@app.get("/health")
def health():
    return {"ok": True, "stt": STT_MODEL, "device": STT_DEVICE}


@app.post("/stt")
async def stt(audio: UploadFile = File(...)):
    """WAV al, Türkçe metin döndür."""
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(await audio.read())
        tmp.flush()
        segments, info = whisper.transcribe(
            tmp.name,
            language="tr",        # dili sabitlemek tahmin adımını atlatır, hızlandırır
            vad_filter=True,
            beam_size=1,          # sohbet için hız > son kırıntı doğruluk
        )
        text = " ".join(s.text.strip() for s in segments).strip()

    print(f"STT [{info.duration:.1f} sn]: {text}")
    return {"text": text}


class TTSIstek(BaseModel):
    text: str


@app.post("/tts")
def tts(istek: TTSIstek):
    """Metin al, WAV döndür. Piper burada çalışır, Pi'de değil."""
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        subprocess.run(
            [PIPER_BIN, "--model", PIPER_MODEL, "--output_file", tmp.name],
            input=istek.text.encode("utf-8"),
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            check=True,
        )
        tmp.seek(0)
        wav = open(tmp.name, "rb").read()

    print(f"TTS [{len(wav)/1024:.0f} KB]: {istek.text[:60]}")
    return Response(content=wav, media_type="audio/wav")
