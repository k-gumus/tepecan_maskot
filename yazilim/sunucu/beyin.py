#!/usr/bin/env python3
"""
Tepecan beyin sunucusu — ses->metin ve metin->ses.

Bu işler maskotun içindeki ESP32 için fazla ağır; buraya alındı. LLM ayrı
bir servis (Ollama) olarak aynı makinede çalışır, sunucu ona bağlanır.

    uvicorn beyin:app --host 0.0.0.0 --port 8000

Ortam değişkenleri:
    STT_MODEL=small        CPU'da makul, Türkçesi iyi (varsayılan)
    STT_DEVICE=cuda        GPU varsa
    PIPER_MODEL=/yol/tr_TR-dfki-medium.onnx
"""

import os
import pathlib
import subprocess
import tempfile

import requests
from fastapi import FastAPI, File, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from faster_whisper import WhisperModel

STT_MODEL = os.getenv("STT_MODEL", "small")
STT_DEVICE = os.getenv("STT_DEVICE", "cpu")
STT_COMPUTE = os.getenv("STT_COMPUTE", "int8" if STT_DEVICE == "cpu" else "float16")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
OLLAMA_MODEL = os.getenv("TEPECAN_MODEL", "qwen3:4b")

PIPER_BIN = os.getenv("PIPER_BIN", "piper")
PIPER_MODEL = os.getenv("PIPER_MODEL",
                        os.path.expanduser("~/piper/tr_TR-dfki-medium.onnx"))

BURASI = pathlib.Path(__file__).resolve().parent


def _oku(ad, yedek=""):
    try:
        return (BURASI / ad).read_text(encoding="utf-8").strip()
    except OSError:
        return yedek


PERSONA = _oku("persona.txt", "Sen Tepecan'sın, Yeditepe IEEE kulübünün maskotu.")
BILGILER = _oku("bilgiler.txt")

print(f"faster-whisper yükleniyor: {STT_MODEL} ({STT_DEVICE}/{STT_COMPUTE})")
whisper = WhisperModel(STT_MODEL, device=STT_DEVICE, compute_type=STT_COMPUTE)
print("Hazır.")

app = FastAPI(title="Tepecan beyin")


@app.get("/health")
def health():
    return {"ok": True, "stt": STT_MODEL, "device": STT_DEVICE}


def _cozumle(wav_baytlari: bytes) -> str:
    with tempfile.NamedTemporaryFile(suffix=".wav") as tmp:
        tmp.write(wav_baytlari)
        tmp.flush()
        segments, info = whisper.transcribe(
            tmp.name,
            language="tr",        # dili sabitlemek tahmin adımını atlatır, hızlandırır
            vad_filter=True,
            beam_size=1,          # sohbet için hız > son kırıntı doğruluk
        )
        text = " ".join(s.text.strip() for s in segments).strip()

    print(f"STT [{info.duration:.1f} sn]: {text}")
    return text


@app.post("/stt")
async def stt(audio: UploadFile = File(...)):
    """WAV dosya yüklemesi al, Türkçe metin döndür (Python istemcisi)."""
    return {"text": _cozumle(await audio.read())}


@app.post("/stt-raw")
async def stt_raw(request: Request):
    """Ham WAV gövdesi al, Türkçe metin döndür.

    ESP32 için: mikrodenetleyicide multipart/form-data kurmak gereksiz
    zahmet, gövdeye doğrudan WAV koyup göndermek yetiyor.
    """
    return {"text": _cozumle(await request.body())}


class SohbetIstek(BaseModel):
    text: str


@app.post("/chat")
def chat(istek: SohbetIstek):
    """Soruyu Ollama'ya sor, cevabı düz metin olarak döndür.

    Akan JSON'u ayrıştırmayı ve cümlelere bölmeyi burada yapıyoruz;
    ESP32'ye yaptırmak gereksiz karmaşıklık. Kart yalnız soruyu yollayıp
    cevabı alıyor.
    """
    mesajlar = [{"role": "system", "content": PERSONA + "\n\n" + BILGILER},
                {"role": "user", "content": istek.text}]
    r = requests.post(
        f"{OLLAMA_URL}/api/chat",
        json={"model": OLLAMA_MODEL, "messages": mesajlar, "stream": False,
              "options": {"temperature": 0.7, "num_predict": 200}},
        timeout=120,
    )
    r.raise_for_status()
    cevap = r.json().get("message", {}).get("content", "").strip()

    # qwen3 gibi modeller düşünme bloğu yazabiliyor; seslendirmeden önce at.
    if "</think>" in cevap:
        cevap = cevap.split("</think>", 1)[1].strip()

    print(f"LLM: {cevap[:80]}")
    return {"text": cevap}


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
