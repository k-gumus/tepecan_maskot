# Tepecan

Yeditepe IEEE kulübünün resmi maskotu — 3D baskı gövde ve içine giren sesli
asistan. Dinler, sorulanı yapay zekâya iletir, cevabı Türkçe olarak
hoparlöründen söyler.

<p align="center">
  <img src="govde/preview/tepecan_views.png" width="100%">
</p>

- **240 mm** boy, tek parça basılan gövde
- Sırtta **vidalı kapak**, içinde 65 × 54 × 63 mm elektronik bölmesi
- Göğüste kabartma **IEEE** ve **YEDİTEPE**, sol omuzda **7** rozeti
- Beyin ağdaki bir PC'de çalışır: **token maliyeti yok, internet gerekmez**

---

## Depoda ne var

```
govde/        3D model — parametrik script, baskıya hazır STL'ler, önizlemeler
yazilim/      maskot/ (Pi üzerinde çalışan program) ve sunucu/ (ses↔metin servisi)
dokuman/      16 sayfalık yapım kılavuzu (PDF), bağlantı şeması, üretim scriptleri
```

**Başlarken okunacak tek dosya:** [`dokuman/Tepecan_Yapim_Kilavuzu.pdf`](dokuman/Tepecan_Yapim_Kilavuzu.pdf)
— malzeme listesinden montaja, kuruluma ve sorun gidermeye kadar her şey orada.

---

## Nasıl çalışıyor

```
   MASKOT (Pi Zero 2 W)                    BEYİN SUNUCUSU (bir PC)
   butona basılır
   mikrofon kaydeder      ──── Wi-Fi ───▶  /stt    faster-whisper   (ses → metin)
                                           :11434  Ollama, qwen3:4b (cevabı üretir)
   hoparlör çalar         ◀─── Wi-Fi ────  /tts    Piper            (metin → ses)
```

Maskotun içindeki Pi'nin tek işi mikrofonu okuyup hoparlöre yazmak. Ses→metin,
dil modeli ve metin→ses, ağdaki bir bilgisayarda çalışır. Bu yüzden 512 MB
RAM'li küçük bir kart yetiyor ve kullanım başına maliyet oluşmuyor.

Cevap tamamlanmadan konuşmaya başlar: model ilk cümleyi bitirir bitirmez o
cümle seslendirilir, kalanı arka planda üretilir.

<p align="center">
  <img src="dokuman/devre_semasi.png" width="100%">
</p>

---

## Gövde

```bash
cd govde
pip install -r requirements.txt
python3 tepecan_model.py                 # 240 mm, stl/ klasörünü üretir
python3 tepecan_model.py --height 180    # daha küçük baskı, cidar yine 3 mm
python3 preview_render.py                # önizleme görselleri
```

| Dosya | Ne |
|---|---|
| `stl/tepecan_body.stl` | İçi boş gövde — sırt açıklığı, kapak kenarı, vida kulakları |
| `stl/tepecan_lid.stl` | Sırt kapağı, baskı pozisyonunda |
| `stl/tepecan_solid.stl` | İçi dolu vitrin figürü (elektronik yoksa bunu bas) |

Figür tasarım biriminde modellenip export'ta ölçekleniyor; cidar kalınlığı,
vida delikleri ve kapak boşluğu gibi mutlak kalması gereken ölçüler önce bu
ölçeğe bölünüyor — böylece M3 vida her boyda M3 kalıyor.

Script her STL'i yazdıktan sonra dosyayı geri okuyup kapalı (watertight),
tutarlı normalli, tek parça ve pozitif hacimli olduğunu doğruluyor; geçmezse
hata verip duruyor.

**Baskı:** PLA, 0.20 mm katman, 3 perimetre, %10-15 dolgu, ağaç destek açık,
5 mm brim. Z ekseni ≥ 250 mm olan yazıcı gerekiyor.

---

## Yazılım

**Sunucu** (kulüpteki PC):

```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen3:4b
OLLAMA_HOST=0.0.0.0 ollama serve

cd yazilim/sunucu
pip install -r requirements.txt
uvicorn beyin:app --host 0.0.0.0 --port 8000
```

**Maskot** (Raspberry Pi Zero 2 W):

```bash
cd yazilim/maskot
pip install -r requirements.txt
python3 tepecan.py
```

Butona bas, konuş, bırak — kayıt sen susunca kendiliğinden biter.

### Ayarlar

| Değişken | Varsayılan | Ne işe yarar |
|---|---|---|
| `TEPECAN_BRAIN` | `http://tepecan-beyin.local` | Beyin sunucusunun adresi |
| `TEPECAN_MODEL` | `qwen3:4b` | Ollama'da kullanılacak model |
| `TEPECAN_LLM_BACKEND` | `ollama` | `ollama` veya `claude` |
| `TEPECAN_BUTTON_PIN` | `17` | Butonun bağlı olduğu GPIO |
| `STT_MODEL` / `STT_DEVICE` | `small` / `cpu` | Sunucuda whisper boyutu ve cihazı |
| `PIPER_MODEL` | `~/piper/tr_TR-dfki-medium.onnx` | Sunucuda Türkçe ses modeli |

### Küçük modelden iyi cevap almak

Model 4 milyar parametreli; ondan bilgiyi *bilmesini* değil, verdiğimiz metni
*okumasını* istiyoruz. Kaliteyi belirleyen sıra:

1. **`yazilim/maskot/bilgiler.txt` dosyasını doldur.** Kulübe dair her gerçek
   buraya; her soruda modele veriliyor. Doğru cevabı sağlayan asıl mekanizma bu.
2. `persona.txt` içindeki 2-3 cümle sınırını gevşetme — küçük modeller
   uzadıkça dağılır.
3. Hafıza 6 mesajla sınırlı ve 3 dakika sessizlikte sıfırlanıyor; artırma.

---

## Lisans

MIT — bkz. [LICENSE](LICENSE).
