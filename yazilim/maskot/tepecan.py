#!/usr/bin/env python3
"""
Tepecan — maskotun içindeki sesli asistan.

Raspberry Pi Zero 2 W üzerinde çalışır. Pi'nin tek işi mikrofonu okumak ve
hoparlöre yazmak; ses->metin, LLM ve metin->ses beyin sunucusunda.

    buton -> kayıt (sen susunca biter) -> /stt -> Ollama -> cümle cümle /tts -> hoparlör

Ayarların hepsi ortam değişkeninden okunur, hepsinin varsayılanı vardır.
"""

import json
import os
import queue
import re
import sys
import threading
import time
import wave
from io import BytesIO

import requests
import sounddevice as sd
import webrtcvad

# --------------------------------------------------------------------------
# Ayarlar
# --------------------------------------------------------------------------
BRAIN = os.getenv("TEPECAN_BRAIN", "http://tepecan-beyin.local")
STT_URL = f"{BRAIN}:8000/stt"
TTS_URL = f"{BRAIN}:8000/tts"
OLLAMA_URL = f"{BRAIN}:11434"
OLLAMA_MODEL = os.getenv("TEPECAN_MODEL", "qwen3:4b")

LLM_BACKEND = os.getenv("TEPECAN_LLM_BACKEND", "ollama")   # ollama | claude
CLAUDE_MODEL = "claude-opus-5"

BUTTON_PIN = int(os.getenv("TEPECAN_BUTTON_PIN", "17"))    # ReSpeaker HAT butonu
MIC_RATE = 16000                 # STT ve VAD 16 kHz ister
FRAME_MS = 30                    # webrtcvad 10/20/30 ms kabul eder
SILENCE_MS = 800                 # bu kadar sessizlikte kayıt biter
MAX_RECORD_S = 15                # güvenlik sınırı
MEMORY_TURNS = 6                 # kaç mesaj hatırlansın (küçük modelde artırma)
MEMORY_TIMEOUT_S = 180           # bu kadar sessizlikten sonra sohbeti sıfırla

HERE = os.path.dirname(os.path.abspath(__file__))


def _read(name, fallback=""):
    path = os.path.join(HERE, name)
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            return f.read().strip()
    return fallback


PERSONA = _read("persona.txt", "Sen Tepecan'sın, sevimli bir kulüp maskotusun.")
FACTS = _read("bilgiler.txt")
SYSTEM_PROMPT = PERSONA + (("\n\nBildiklerin:\n" + FACTS) if FACTS else "")


def set_state(state):
    """bekliyor | dinliyor | dusunuyor | konusuyor — LED takarsan buraya bağla."""
    print(f"[{state}]", flush=True)


# --------------------------------------------------------------------------
# 1) Mikrofon: konuşma bitene kadar kaydet
# --------------------------------------------------------------------------
def record_until_silence():
    vad = webrtcvad.Vad(2)                    # 0 gevşek .. 3 agresif
    frame_len = int(MIC_RATE * FRAME_MS / 1000)
    silence_limit = SILENCE_MS // FRAME_MS

    frames, silent, started = [], 0, False
    deadline = time.time() + MAX_RECORD_S

    with sd.RawInputStream(samplerate=MIC_RATE, blocksize=frame_len,
                           dtype="int16", channels=1) as stream:
        while time.time() < deadline:
            block, overflowed = stream.read(frame_len)
            if overflowed:
                continue
            block = bytes(block)
            frames.append(block)

            if vad.is_speech(block, MIC_RATE):
                started, silent = True, 0
            elif started:
                silent += 1
                if silent >= silence_limit:
                    break

    if not started:
        return None

    buf = BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(MIC_RATE)
        wav.writeframes(b"".join(frames))
    return buf.getvalue()


# --------------------------------------------------------------------------
# 2) Ses -> metin (beyin sunucusu)
# --------------------------------------------------------------------------
def transcribe(wav_bytes):
    r = requests.post(STT_URL, files={"audio": ("ses.wav", wav_bytes, "audio/wav")},
                      timeout=60)
    r.raise_for_status()
    return r.json().get("text", "").strip()


# --------------------------------------------------------------------------
# 3) LLM — iki arka uç, aynı arayüz: metin parçaları üreten jeneratör
# --------------------------------------------------------------------------
THINK_TAG = re.compile(r"<think>.*?</think>", re.S)


def stream_ollama(messages):
    payload = {
        "model": OLLAMA_MODEL,
        "messages": [{"role": "system", "content": SYSTEM_PROMPT}] + messages,
        "stream": True,
        "think": False,               # Qwen3'te düşünme modunu kapat
        "options": {
            "temperature": 0.7,
            "repeat_penalty": 1.15,   # küçük modeller kendini tekrarlar
            "num_predict": 160,       # kısa tut; hoparlörden kompozisyon dinlemeyelim
            "num_ctx": 2048,
        },
    }
    with requests.post(f"{OLLAMA_URL}/api/chat", json=payload,
                       stream=True, timeout=120) as r:
        r.raise_for_status()
        for line in r.iter_lines():
            if not line:
                continue
            chunk = json.loads(line)
            piece = chunk.get("message", {}).get("content", "")
            if piece:
                yield piece
            if chunk.get("done"):
                break


def stream_claude(messages):
    import anthropic

    client = anthropic.Anthropic()
    with client.messages.stream(
        model=CLAUDE_MODEL,
        max_tokens=400,
        system=[{"type": "text", "text": SYSTEM_PROMPT,
                 "cache_control": {"type": "ephemeral"}}],   # kişilik her turda aynı
        output_config={"effort": "low"},                     # sohbet için hızlı
        messages=messages,
    ) as stream:
        for text in stream.text_stream:
            yield text


def stream_reply(messages):
    return stream_claude(messages) if LLM_BACKEND == "claude" else stream_ollama(messages)


# --------------------------------------------------------------------------
# 4) Cümle bölücü — ilk cümle biter bitmez konuşmaya başlamak için
# --------------------------------------------------------------------------
SENTENCE_END = re.compile(r"[.!?…:;]\s|\n")


def sentences(token_stream):
    buf = ""
    for piece in token_stream:
        buf = THINK_TAG.sub("", buf + piece)
        while True:
            m = SENTENCE_END.search(buf)
            if not m:
                break
            head, buf = buf[:m.end()].strip(), buf[m.end():]
            if len(head) >= 2:
                yield head
    tail = THINK_TAG.sub("", buf).strip()
    if tail:
        yield tail


# --------------------------------------------------------------------------
# 5) Metin -> ses (beyin sunucusu üretir, Pi sadece çalar)
# --------------------------------------------------------------------------
def speak(text):
    r = requests.post(TTS_URL, json={"text": text}, timeout=60)
    r.raise_for_status()

    with wave.open(BytesIO(r.content), "rb") as wav:
        rate = wav.getframerate()
        data = wav.readframes(wav.getnframes())

    with sd.RawOutputStream(samplerate=rate, channels=1, dtype="int16") as out:
        out.write(data)


def speaker_thread(q):
    while True:
        text = q.get()
        if text is None:
            return
        try:
            speak(text)
        except Exception as exc:
            print(f"TTS hatası: {exc}")
        q.task_done()


# --------------------------------------------------------------------------
# 6) Tetikleyici: omuzdaki butona bas (kart yoksa Enter)
# --------------------------------------------------------------------------
def make_trigger():
    try:
        from gpiozero import Button
        button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.05)
        print(f"Buton GPIO{BUTTON_PIN}. Bas ve konuş.")
        return button.wait_for_press
    except Exception as exc:
        print(f"Buton yok ({exc}); Enter'a basarak konuş.")
        return lambda: input()


# --------------------------------------------------------------------------
def main():
    trigger = make_trigger()
    tts_queue = queue.Queue()
    threading.Thread(target=speaker_thread, args=(tts_queue,), daemon=True).start()

    history, last_turn = [], 0.0
    print(f"Tepecan hazır. Beyin: {BRAIN} | LLM: {LLM_BACKEND} "
          f"({OLLAMA_MODEL if LLM_BACKEND == 'ollama' else CLAUDE_MODEL})")

    while True:
        set_state("bekliyor")
        trigger()

        set_state("dinliyor")
        wav = record_until_silence()
        if not wav:
            continue

        set_state("dusunuyor")
        try:
            question = transcribe(wav)
        except Exception as exc:
            print(f"STT hatası: {exc}")
            tts_queue.put("Kusura bakma, seni duyamadım.")
            continue
        if not question:
            continue
        print(f"> {question}")

        if time.time() - last_turn > MEMORY_TIMEOUT_S:
            history.clear()
        last_turn = time.time()

        history.append({"role": "user", "content": question})
        del history[:-MEMORY_TURNS]

        answer = ""
        set_state("konusuyor")
        try:
            for sentence in sentences(stream_reply(history)):
                print(f"< {sentence}")
                answer += sentence + " "
                tts_queue.put(sentence)
        except Exception as exc:
            print(f"LLM hatası: {exc}")
            tts_queue.put("Şu an kafam çalışmıyor, birazdan tekrar dene.")
            continue

        tts_queue.join()
        if answer.strip():
            history.append({"role": "assistant", "content": answer.strip()})


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
