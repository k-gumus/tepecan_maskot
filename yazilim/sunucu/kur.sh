#!/usr/bin/env bash
# Tepecan beyin sunucusu kurulumu - kulüpteki PC'de bir kez çalıştırılır.
#
#   bash kur.sh
#
# Kurduğu şeyler:
#   1. Ollama + dil modeli      (cevabı üreten)
#   2. Python bağımlılıkları    (faster-whisper, FastAPI)
#   3. Piper + Türkçe ses       (metni sese çeviren)
#
# Linux ve macOS'ta doğrudan, Windows'ta WSL2 içinde çalışır.
set -euo pipefail

MODEL="${TEPECAN_MODEL:-qwen3:4b}"
SES="tr_TR-dfki-medium"
SES_DIZIN="${HOME}/piper"
SES_URL="https://huggingface.co/rhasspy/piper-voices/resolve/main/tr/tr_TR/dfki/medium"

bilgi() { printf '\n\033[1;34m==>\033[0m %s\n' "$1"; }
hata()  { printf '\n\033[1;31mHATA:\033[0m %s\n' "$1" >&2; exit 1; }

# ------------------------------------------------------------------ 1/3
bilgi "1/3  Ollama ve dil modeli"
if ! command -v ollama >/dev/null 2>&1; then
    echo "Ollama kurulu değil, kuruluyor..."
    curl -fsSL https://ollama.com/install.sh | sh \
        || hata "Ollama kurulamadı. Elle: https://ollama.com/download"
else
    echo "Ollama zaten kurulu: $(ollama --version 2>/dev/null || echo '?')"
fi

# Model çekmek için servisin ayakta olması lazım.
if ! curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1; then
    echo "Ollama servisi arka planda başlatılıyor..."
    (OLLAMA_HOST=0.0.0.0 nohup ollama serve >/tmp/ollama.log 2>&1 &) || true
    for _ in $(seq 1 30); do
        curl -sf http://127.0.0.1:11434/api/version >/dev/null 2>&1 && break
        sleep 1
    done
fi

echo "Model indiriliyor: ${MODEL}  (birkaç GB, sabır)"
ollama pull "${MODEL}" || hata "Model indirilemedi: ${MODEL}"

# ------------------------------------------------------------------ 2/3
bilgi "2/3  Python bağımlılıkları"
command -v python3 >/dev/null 2>&1 || hata "python3 bulunamadı."
python3 -m venv .venv 2>/dev/null || true
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip >/dev/null
pip install -r requirements.txt
pip install piper-tts || echo "UYARI: piper-tts pip ile kurulamadı, aşağıya bak."

# ------------------------------------------------------------------ 3/3
bilgi "3/3  Türkçe ses modeli"
mkdir -p "${SES_DIZIN}"
for uzanti in onnx onnx.json; do
    hedef="${SES_DIZIN}/${SES}.${uzanti}"
    if [ -s "${hedef}" ]; then
        echo "zaten var: ${hedef}"
        continue
    fi
    echo "indiriliyor: ${SES}.${uzanti}"
    curl -fL --progress-bar -o "${hedef}" "${SES_URL}/${SES}.${uzanti}" || {
        rm -f "${hedef}"
        hata "Ses modeli inmedi. Elle indirip ${SES_DIZIN}/ içine koy:
     ${SES_URL}/${SES}.${uzanti}
  (Bu adresler betiğe yazılırken doğrulanamadı; Piper sesleri
   huggingface.co/rhasspy/piper-voices altında duruyor.)"
    }
done

# ------------------------------------------------------------------ bitti
cat <<BITTI

============================================================
Kurulum bitti.

Sunucuyu başlatmak için, bu klasörde:

    source .venv/bin/activate
    OLLAMA_HOST=0.0.0.0 ollama serve &                  # ayakta değilse
    PIPER_MODEL=${SES_DIZIN}/${SES}.onnx \\
      uvicorn beyin:app --host 0.0.0.0 --port 8000

Çalıştığını doğrula:

    curl http://127.0.0.1:8000/health

ESP32'nin bu makineye ulaşabilmesi için aynı ağda olmalı ve
güvenlik duvarında 8000 ile 11434 portları açık olmalı.
Kartın kurulum sayfasına yazacağın adres:

    http://<bu-bilgisayarin-IP-adresi>:8000
============================================================
BITTI
