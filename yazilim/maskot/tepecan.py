#!/usr/bin/env python3
"""
Tepecan — maskotun içindeki sesli asistan.

Raspberry Pi Zero 2 W üzerinde çalışır. Pi'nin tek işi mikrofonu okumak ve
hoparlöre yazmak; ses->metin, LLM ve metin->ses beyin sunucusunda.

    "Hey Tepecan" (ya da buton)
        -> kayıt (sen susunca biter) -> /stt -> Ollama -> cümle cümle /tts -> hoparlör

Mikrofon tek bir sürekli akış olarak açılır; uyandırma kelimesi dedektörü ve
kayıt aynı akıştan beslenir. Ayarların hepsi ortam değişkeninden okunur.
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

import numpy as np
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
WAKE_MODEL = os.getenv("TEPECAN_WAKE_MODEL",               # boş -> sadece buton
                       os.path.expanduser("~/tepecan/hey_tepecan.onnx"))
WAKE_THRESHOLD = float(os.getenv("TEPECAN_WAKE_THRESHOLD", "0.5"))
WAKE_HITS = int(os.getenv("TEPECAN_WAKE_HITS", "2"))       # ardışık kaç blok eşiği aşmalı

MIC_RATE = 16000                 # STT, VAD ve uyandırma modeli 16 kHz ister
BLOCK = 1280                     # 80 ms — openWakeWord'ün beklediği pencere
VAD_FRAME = 160                  # 10 ms — webrtcvad'in kabul ettiği en küçük pencere
VAD_BYTES = VAD_FRAME * 2
VOICED_FRAMES = 3                # 80 ms içinde en az 30 ms konuşma varsa "konuşuyor"
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
# 1) Mikrofon — tek sürekli akış
# --------------------------------------------------------------------------
vad = webrtcvad.Vad(2)           # 0 gevşek .. 3 agresif


def speaking(block):
    """80 ms'lik bloğu 10 ms'lik parçalara bölüp VAD'e sorar."""
    voiced = sum(vad.is_speech(block[i:i + VAD_BYTES], MIC_RATE)
                 for i in range(0, len(block), VAD_BYTES))
    return voiced >= VOICED_FRAMES


def drain(mic):
    """Biriken sesi at. Tepecan kendi konuşmasını duymasın diye şart."""
    while mic.read_available >= BLOCK:
        mic.read(BLOCK)


class WakeWord:
    """openWakeWord sarmalayıcısı. Model yoksa sessizce devre dışı kalır."""

    def __init__(self, model_path, threshold, needed_hits):
        self.model, self.threshold, self.needed = None, threshold, needed_hits
        self.hits = 0
        if not model_path or not os.path.exists(model_path):
            print(f"Uyandırma modeli yok ({model_path}); sadece buton çalışır.")
            return
        try:
            from openwakeword.model import Model
            self.model = Model(wakeword_models=[model_path], inference_framework="onnx")
            print(f"Uyandırma kelimesi hazır: {os.path.basename(model_path)} "
                  f"(eşik {threshold})")
        except Exception as exc:
            print(f"Uyandırma kelimesi yüklenemedi ({exc}); sadece buton çalışır.")

    @property
    def enabled(self):
        return self.model is not None

    def reset(self):
        self.hits = 0
        if self.model is not None and hasattr(self.model, "reset"):
            self.model.reset()

    def hears(self, block):
        if self.model is None:
            return False
        scores = self.model.predict(np.frombuffer(block, dtype=np.int16))
        best = max(scores.values()) if scores else 0.0
        self.hits = self.hits + 1 if best >= self.threshold else 0
        if self.hits >= self.needed:
            self.reset()
            return True
        return False


def wait_for_trigger(mic, wake, button):
    """Uyandırma kelimesi ya da butona basılana kadar bekler."""
    wake.reset()
    while True:
        block, _ = mic.read(BLOCK)
        block = bytes(block)
        if button is not None and button.is_pressed:
            while button.is_pressed:            # bırakılmasını bekle
                time.sleep(0.02)
            return "buton"
        if wake.hears(block):
            return "kelime"


def record_until_silence(mic):
    """Konuşma bitene kadar kaydeder, 16 kHz mono WAV baytları döndürür."""
    silence_limit = SILENCE_MS // (BLOCK * 1000 // MIC_RATE)
    frames, silent, started = [], 0, False
    deadline = time.time() + MAX_RECORD_S

    while time.time() < deadline:
        block, _ = mic.read(BLOCK)
        block = bytes(block)
        frames.append(block)

        if speaking(block):
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
# 6) Buton — uyandırma kelimesi çalışsa da yedek olarak duruyor
# --------------------------------------------------------------------------
def make_button():
    try:
        from gpiozero import Button
        button = Button(BUTTON_PIN, pull_up=True, bounce_time=0.05)
        print(f"Buton GPIO{BUTTON_PIN}.")
        return button
    except Exception as exc:
        print(f"Buton yok ({exc}).")
        return None


# --------------------------------------------------------------------------
def main():
    button = make_button()
    wake = WakeWord(WAKE_MODEL, WAKE_THRESHOLD, WAKE_HITS)
    if button is None and not wake.enabled:
        sys.exit("Ne buton ne uyandırma kelimesi var; tetikleyici olmadan çalışamam.")

    tts_queue = queue.Queue()
    threading.Thread(target=speaker_thread, args=(tts_queue,), daemon=True).start()

    history, last_turn = [], 0.0
    print(f"Tepecan hazır. Beyin: {BRAIN} | LLM: {LLM_BACKEND} "
          f"({OLLAMA_MODEL if LLM_BACKEND == 'ollama' else CLAUDE_MODEL})")

    with sd.RawInputStream(samplerate=MIC_RATE, blocksize=BLOCK,
                           dtype="int16", channels=1) as mic:
        while True:
            set_state("bekliyor")
            drain(mic)
            how = wait_for_trigger(mic, wake, button)

            set_state("dinliyor")
            print(f"({how} ile uyandı)")
            wav = record_until_silence(mic)
            if not wav:
                continue

            # Bundan sonrası mikrofonu gerektirmiyor. Kapatmak üç işi birden
            # çözüyor: Tepecan kendi sesini duymuyor, ses kartından aynı anda
            # hem giriş hem çıkış istenmiyor, ve tampon boşuna dolmuyor.
            mic.stop()
            try:
                set_state("dusunuyor")
                try:
                    question = transcribe(wav)
                except Exception as exc:
                    print(f"STT hatası: {exc}")
                    tts_queue.put("Kusura bakma, seni duyamadım.")
                    tts_queue.join()
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
                    tts_queue.join()
                    continue

                tts_queue.join()
                if answer.strip():
                    history.append({"role": "assistant", "content": answer.strip()})
            finally:
                mic.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
