# Tepecan — sesli asistan maskot: ESP32-S3 istemcisi + PC sunucusu

Aşağıdaki projenin **tüm kodunu** sıfırdan yaz. İki taraf var ve ikisi aynı
protokolü konuşmak zorunda; birini yazıp diğerini uydurma, ikisini birlikte
tasarla.

Kod yorumları **Türkçe** olsun. Değişken ve fonksiyon adları da Türkçe olabilir
(mevcut proje öyle). Yorum yazarken "ne yaptığını" değil **"neden öyle
yaptığını"** yaz — özellikle bir tuzaktan kaçınmak için yapılan seçimlerde.

---

## 1. Ne yapıyor

Masaüstü boyutunda bir maskot figürünün içinde ESP32-S3 var. Kullanıcı
"uyandırma kelimesini" söylüyor ya da sırtındaki butona basıyor; maskot
dinliyor, sorduğu soruyu bir PC'ye gönderiyor, PC ses→metin→cevap→ses
zincirini çalıştırıp sesi geri gönderiyor, maskot hoparlöründen çalıyor.

Ağır işin **hiçbiri** ESP32'de değil. Kartın tek işi: mikrofonu okumak,
soketten akıtmak, gelen sesi hoparlöre yazmak, butona ve LED'e bakmak.

---

## 2. Donanım — birebir bu

**Kart:** ESP32-S3-DevKitC-1 N16R8 (16 MB flash, 8 MB PSRAM).
**Mikrofon:** INMP441 (I2S).
**Amfi:** MAX98357A (I2S, sınıf D).
**Hoparlör:** Ø30 mm, 4 Ω 3 W.
**Buton:** tactile switch, bir bacağı GPIO'ya, diğeri GND'ye.

Pin haritası (bunları `tepecan.h` içinde `#define` yap, kodun içine gömme):

| İşlev | GPIO |
|---|---|
| INMP441 SCK (bit clock) | 4 |
| INMP441 WS (word select) | 5 |
| INMP441 SD (veri çıkışı) | 6 |
| MAX98357A BCLK | 15 |
| MAX98357A LRC | 16 |
| MAX98357A DIN | 17 |
| Buton | 18 (dahili pull-up, basınca GND) |
| Yerleşik RGB LED | 48 (WS2812, adreslenebilir) |

Donanımla ilgili, koda yansıyan gerçekler:

- **INMP441 24-bit veriyi 32-bit yuvaya koyuyor.** I2S'i
  `I2S_DATA_BIT_WIDTH_32BIT` ve `I2S_SLOT_MODE_MONO` ile aç, `int32_t`
  olarak oku, sonra `>> 11` ile 16-bit'e indir ve `int16_t`'ye kırp.
  Doğrudan 16-bit okumaya çalışırsan çöp gelir.
- INMP441'in **L/R bacağı GND'ye** bağlı → sol kanaldan konuşuyor.
  `slot_mask = I2S_STD_SLOT_LEFT`.
- **MAX98357A köprü bağlı (BTL).** Hoparlörün iki ucu da sürülüyor, hiçbiri
  GND'ye gitmez. README'de bunu yaz.
- Mikrofon `I2S_NUM_0`, hoparlör `I2S_NUM_1` — ayrı kanallar.
- Yerleşik LED adreslenebilir WS2812, düz GPIO değil. `led_strip` bileşeni
  gerekiyor. Bazı revizyonlarda GPIO 38; `#define` ile değiştirilebilir olsun.

---

## 3. Mimari kararı

ESP32 ile PC **ham TCP soketiyle**, kendi ikili protokolümüzle konuşuyor.
HTTP yok, JSON yok, base64 yok.

Uyandırma kelimesi **PC'de** çalışıyor (openWakeWord). ESP32 mikrofonu
sürekli akıtıyor. Böylece karta model eğitip yüklemek gerekmiyor ve
uyandırma kelimesini değiştirmek sunucuda tek satır.

Bunun bedeli: ESP32 Wi-Fi'ye bağlı değilken hiçbir şey yapamıyor. Kabul.

---

## 4. Protokol — bayt bayt tanımlı

TCP, varsayılan port **6000**. **ESP32 istemci, PC sunucu.** Tüm sayılar
**little-endian**.

Her mesajın başlığı aynı:

```
offset 0: uint8   tip
offset 1: uint32  govde_uzunlugu   (bayt; başlık dahil değil)
offset 5: govde   (govde_uzunlugu bayt)
```

### ESP32 → PC

| tip | ad | gövde |
|---|---|---|
| 0x01 | `SES` | 16-bit LE PCM, 16 kHz, mono. Her mesaj **320 örnek = 640 bayt** (20 ms). |
| 0x02 | `BUTON` | boş. Butona basıldı, uyandırma kelimesini beklemeden kayda geç. |
| 0x03 | `PING` | boş. 5 saniyede bir, bağlantı canlı mı. |

### PC → ESP32

| tip | ad | gövde |
|---|---|---|
| 0x10 | `KONUS_BASLA` | `uint32 toplam_bayt` + `uint32 ornekleme_hz` |
| 0x11 | `KONUS_PARCA` | PCM parçası, en fazla 4096 bayt |
| 0x12 | `KONUS_BITTI` | boş |
| 0x13 | `DURUM` | `uint8 durum` — LED rengi için (aşağıdaki durum makinesi) |
| 0x14 | `PONG` | boş |

### Yarı çift yönlü kuralı — bunu atlama, kilitlenirsin

`KONUS_BASLA` geldiği anda ESP32 **mikrofonu susturur ve `SES` göndermeyi
bırakır**; `KONUS_BITTI`'ye kadar yalnız dinler. `PING` göndermeye devam
edebilir.

Sunucu tarafında da simetrik kural: konuşurken gelen `SES` mesajları
**okunup atılır**, işlenmez (yoldaki paketler için).

Bu kuralın sebebi somut: sunucu birkaç yüz kilobayt PCM gönderirken soketten
okumayı bırakırsa, ESP32'nin mikrofon verisi çekirdek tamponunu doldurur,
ESP32'nin `send`'i bloklanır, ESP32 de çalma verisini okuyamaz ve iki taraf
birbirini bekler. Kilitlenme.

### Kısa okuma — ikinci klasik tuzak

**İki tarafta da** `recv` / `read` istediğin kadar bayt vermeyi garanti
etmiyor; o an tamponda ne varsa onu verir. Her iki tarafta da "tam n bayt
oku" yardımcı fonksiyonu yaz ve **her yerde onu kullan**:

```python
def tam_oku(sock, n):
    buf = bytearray()
    while len(buf) < n:
        parca = sock.recv(n - len(buf))
        if not parca:
            return None          # karşı taraf kapattı
        buf.extend(parca)
    return bytes(buf)
```

Ham `recv(n)` ile gelen kısa bloğu sessizce atmak, hata vermeden sesin
parça parça kaybolmasına ve uyandırma kelimesinin hiç tetiklenmemesine yol
açar. Bu hata ayıklanması en zor hatalardan biri, baştan doğru yap.

---

## 5. ESP32 tarafı

### Ortam

- **ESP-IDF v6.1.** (v5.3 ile de derlenmeli, ama hedef v6.1.)
- Hedef yonga: **esp32s3**.
- Proje yolu ASCII olmalı — Türkçe karakterli ya da OneDrive altındaki bir
  klasörde GCC kendi spec dosyasını açamıyor. README'ye `C:\esp\<proje>`
  yaz.

### v6 tuzakları — bunlar gerçek, ölçüldü

- `driver` bileşeni bölündü. `driver/i2s_std.h` artık **`esp_driver_i2s`**,
  `driver/gpio.h` **`esp_driver_gpio`** içinde. `REQUIRES` satırına ikisini
  de ekle.
- **cJSON çekirdekten çıkarıldı.** `REQUIRES`'a `json` yazarsan
  `Failed to resolve component 'json'` alırsın. Zaten bu protokolde JSON
  yok; hiç kullanma.
- SPIFFS'e ihtiyaç yok, `spiffs` ekleme.

`main/CMakeLists.txt` şuna benzemeli:

```cmake
idf_component_register(
    SRCS "main.c" "ses.c" "ag.c" "portal.c" "led.c"
    INCLUDE_DIRS "."
    REQUIRES esp_driver_i2s esp_driver_gpio driver esp_wifi
             esp_http_server nvs_flash esp_netif esp_psram led_strip
)
```

`sdkconfig.defaults` içinde en az:

```
CONFIG_IDF_TARGET="esp32s3"
CONFIG_ESPTOOLPY_FLASHSIZE_16MB=y
CONFIG_SPIRAM=y
CONFIG_SPIRAM_MODE_OCT=y
CONFIG_SPIRAM_SPEED_80M=y
CONFIG_FREERTOS_HZ=1000
CONFIG_ESP_MAIN_TASK_STACK_SIZE=8192
```

Özel `partitions.csv` yaz (16 MB flash, tek app + nvs).

### Dosya yapısı

```
main/
  main.c        durum makinesi, görevlerin kurulumu
  tepecan.h     pinler, ses sabitleri, durum enum'u
  ses.c/.h      I2S mikrofon + hoparlör
  ag.c/.h       soket istemcisi, protokol kodlama/çözme
  portal.c/.h   ilk açılış Wi-Fi kurulum portalı
  led.c/.h      WS2812 durum göstergesi
  CMakeLists.txt
CMakeLists.txt
sdkconfig.defaults
partitions.csv
README.md
```

### Wi-Fi ve ilk kurulum

- Ayarlar **NVS**'te: `ssid`, `sifre`, `sunucu_ip`, `sunucu_port`.
- NVS boşsa ya da Wi-Fi'ye 3 denemede bağlanılamazsa **kurulum moduna** geç:
  - Kart kendi AP'sini açar: SSID **`Tepecan-Kurulum`**, şifresiz.
  - `192.168.4.1` adresinde küçük bir HTTP sunucusu (`esp_http_server`),
    tek sayfalık form: Wi-Fi adı, şifre, sunucu IP, port.
  - Form gönderilince NVS'e yazar ve yeniden başlar.
  - Formu elle ayrıştır (JSON yok): `application/x-www-form-urlencoded`
    gövdesinden alan çekme fonksiyonu yaz, `%XX` ve `+` çözümlemesi dahil.
- Butona **5 saniye basılı tutmak** NVS'i siler ve kurulum moduna döndürür.
  (Kullanıcı yanlış şifre girerse çıkış yolu olsun.)

### Ses

`ses.c` şunları versin:

```c
esp_err_t mik_baslat(void);
esp_err_t hoparlor_baslat(void);
esp_err_t mik_oku(int16_t *hedef, size_t ornek);       /* 32-bit oku, >>11 */
void      mik_sustur(void);                            /* i2s_channel_disable */
void      mik_ac(void);
esp_err_t hoparlor_cal(const int16_t *pcm, size_t ornek, uint32_t hz);
void      hoparlor_sustur(void);
```

- Örnekleme 16 kHz, blok 320 örnek (20 ms).
- `hoparlor_cal` örnekleme hızı değişirse kanalı yeniden yapılandırsın
  (`i2s_channel_reconfig_std_clock`), sonra tekrar etkinleştirsin.
- **Çalma akışlı olsun.** Gelen `KONUS_PARCA`'yı doğrudan
  `i2s_channel_write`'a ver. `i2s_channel_write` DMA dolduğunda bloklar;
  bu doğal olarak TCP okumasını da yavaşlatır ve akışı dengeler. 300 KB'lık
  cevabı RAM'de biriktirmeye kalkma.
- Hoparlörü konuşma bitince sustur, yoksa MAX98357A açık kalıp cızırdar.

### Görevler (FreeRTOS)

Üç görev:

1. **`gorev_mikrofon`** — 20 ms'lik blokları okur, kuyruğa koyar.
2. **`gorev_ag_gonder`** — kuyruktan alıp `SES` mesajı olarak gönderir,
   5 saniyede bir `PING` atar. Susturulmuşken kuyruğu boşaltır, göndermez.
3. **`gorev_ag_al`** — soketten mesaj okur, tipine göre işler. `KONUS_*`
   geldiğinde doğrudan hoparlöre yazar.

Soketi tek bir yerde aç ve iki görev arasında paylaş; gönderimi bir muteks
ile koru.

### Bağlantı yönetimi

- Soket koparsa: 2 s, 4 s, 8 s, 16 s, sonra 16 s sabit aralıkla yeniden dene.
- `TCP_NODELAY` aç (Nagle 20 ms'lik paketleri biriktirip gecikme ekliyor).
- `SO_KEEPALIVE` aç.
- Bağlanamıyorken LED kırmızı yanıp sönsün.

### Durum makinesi ve LED

```c
typedef enum {
    DURUM_KURULUM,      /* AP açık, portal bekliyor      */
    DURUM_BAGLANIYOR,   /* Wi-Fi ya da soket bekleniyor  */
    DURUM_BEKLIYOR,     /* akıtıyor, uyandırma bekleniyor*/
    DURUM_DINLIYOR,     /* sunucu kayıt alıyor           */
    DURUM_DUSUNUYOR,    /* sunucu cevap üretiyor         */
    DURUM_KONUSUYOR,    /* hoparlör çalıyor              */
    DURUM_HATA,
} tepecan_durum_t;
```

LED renkleri: kurulum = mor nefes, bağlanıyor = sarı yanıp sön,
bekliyor = çok sönük mavi, dinliyor = parlak yeşil, düşünüyor = mavi nefes,
konuşuyor = camgöbeği, hata = kırmızı. Parlaklık `#define` ile ayarlanabilir
olsun (yerleşik LED çok parlak).

Durum **sunucudan** `DURUM` mesajıyla geliyor; ESP32 kendi başına yalnız
kurulum/bağlanıyor/hata durumlarını belirliyor.

### Buton

- Dahili pull-up, basınca GND.
- **Yazılımda geri sekme (debounce)**: 50 ms.
- Kısa basış → `BUTON` mesajı gönder.
- Konuşurken kısa basış → çalmayı kes (`hoparlor_sustur`) ve `BUTON` gönder;
  kullanıcı sözünü kesebilsin.
- 5 saniye basılı → NVS sil, yeniden başlat.

---

## 6. PC sunucusu

### Ortam

Python 3.10+. `requirements.txt` yaz. Bağımlılıklar:

```
openwakeword
onnxruntime
faster-whisper
requests
edge-tts
pydub
numpy
```

Ayrıca **sistem paketi olarak `ffmpeg`** gerekiyor — `pydub` mp3 çözmek için
onu çağırıyor. Yoksa `AudioSegment.from_file(..., format="mp3")` patlıyor.
README'de yaz.

### openWakeWord — iki kesin tuzak

1. `pip install openwakeword` modelleri **getirmiyor**. Paketle gelen yollar
   `.tflite`; `inference_framework="onnx"` seçersen kütüphane yolu
   `.onnx` olarak üretiyor ama **dosya var mı diye bakmıyor**, sonra
   onnxruntime dosyayı açamayıp patlıyor. Açılışta bir kez:

   ```python
   from openwakeword.utils import download_models
   download_models(model_names=["alexa"])   # hem tflite hem onnx iner
   ```

2. `onnxruntime` kurulu değilse `Model(...)` doğrudan `ValueError` atıyor.

Ayrıca:

- `predict()`'e **1280 örneklik** (80 ms) bloklar ver. Protokolde 320
  örneklik geliyor, sunucuda **dörder blok biriktir**.
- Tespitten sonra **`model.reset()`** çağır, yoksa kendi iç tamponuyla arka
  arkaya tetikliyor.
- Hazır modeller yalnız: `alexa`, `hey_mycroft`, `hey_jarvis`, `hey_rhasspy`,
  `timer`, `weather`. Model adı ve eşik ayar dosyasından okunsun.

### Kayıt bitişi (endpointing)

Sabit enerji eşiği kullanma, ortam gürültüsüne göre kayıyor. Bunun yerine:

- Uyandırmadan sonraki ilk 300 ms'de gürültü tabanını ölç.
- Eşik = `max(taban * 3, alt_sinir)`.
- Eşiğin altında **800 ms** sessizlik → kayıt biter.
- Ama en az **0.5 saniye** ses kaydedilmiş olmalı (yoksa uyandırma
  kelimesinin kuyruğuyla tetiklenip boş kayıt gider).
- En fazla **10 saniye**, sonra zorla kes.
- Kaydın başına uyandırma öncesi **0.5 saniyelik** tamponu ekle — kullanıcı
  çoğu zaman uyandırma kelimesiyle soruyu bitişik söylüyor. Bunun için
  `collections.deque(maxlen=...)` ile sürekli dönen bir ön-tampon tut.

### Zincir

1. **STT:** `faster-whisper`, model adı ayardan (`base` varsayılan),
   `device="cpu"`, `compute_type="int8"`, `language="tr"`.
   Metin boşsa zinciri kes, kısa bir "seni duyamadım" cevabı çal.
2. **LLM:** Ollama `http://127.0.0.1:11434/api/chat`. Model ayardan
   (`qwen3:4b` varsayılan). **Türkçe sistem istemi şart**, yoksa model
   İngilizce cevap veriyor. Sistem istemi ayrı bir `persona.txt`
   dosyasından okunsun, koda gömülmesin. Persona: kısa, samimi, en fazla
   2-3 cümle cevap veren bir kulüp maskotu. `<think>` etiketli düşünme
   bloklarını cevaptan **ayıkla** (qwen3 üretiyor).
   Son 6 turu hatırlayan kısa bir sohbet geçmişi tut.
3. **TTS:** `edge-tts`, ses `tr-TR-AhmetNeural` (ayardan). mp3 gelir;
   `pydub` ile **16 kHz, mono, 16-bit** PCM'e çevir.
   Piper'a geçilebilsin diye TTS'i arkasında iki uygulaması olan tek bir
   arayüzün ardına koy.

### Soket sunucusu

- Her istemci için ayrı thread (`threading.Thread`), ama aynı anda tek
  maskot beklendiğini varsay.
- `socket.SO_REUSEADDR`, `TCP_NODELAY`.
- `conn.settimeout(30)` — kart fişten çekilince thread sonsuza kadar
  beklemesin.
- Mesaj okuma/yazma için tek bir `Protokol` sınıfı yaz; başlık paketleme
  tek yerde olsun.
- Gönderme ayrı bir kilitle korunsun.

### Durum makinesi (sunucu)

```
BEKLIYOR    → her 1280 örnekte openWakeWord çalıştır.
              Tetiklerse ya da BUTON geldiyse → DINLIYOR, DURUM gönder.
DINLIYOR    → ses biriktir, endpointing uygula. Bitince → DUSUNUYOR.
DUSUNUYOR   → STT → LLM → TTS. DURUM gönder.
KONUSUYOR   → KONUS_BASLA, parçalar, KONUS_BITTI. Bu sırada gelen SES atılır.
              Bitince → BEKLIYOR.
```

Zincirin her adımını `logging` ile, geçen süreyi ms cinsinden yazdır —
hangi adımın yavaş olduğunu görmek şart.

### Ayarlar

Tek bir `ayarlar.py` ya da `.env`, ortam değişkeniyle ezilebilir:
port, wake word adı ve eşiği, whisper modeli, Ollama adresi ve modeli,
TTS sesi, sessizlik süresi, en uzun kayıt.

---

## 7. Kabul kriterleri

Kodun bittiğinde şunlar doğru olmalı:

1. Sunucu **kart olmadan** test edilebiliyor: bir WAV dosyasını okuyup
   protokol üzerinden gönderen `test_istemci.py` yaz, cevabı WAV olarak
   kaydetsin. Bütün zincir kartsız denenebilsin.
2. `tam_oku` her iki tarafta da kullanılıyor, çıplak `recv`/`read` yok.
3. Konuşma sırasında mikrofon susuyor ve sunucu gelen sesi atıyor.
4. Soket koparsa ESP32 kendi kendine geri bağlanıyor, elle sıfırlama yok.
5. Wi-Fi bilgisi yanlışsa kart kurulum AP'sine düşüyor, tuğlalaşmıyor.
6. `idf.py build` **temiz bir klasörde**, `sdkconfig` olmadan, hedef
   esp32s3 ile hatasız derleniyor.
7. Sunucu ilk çalıştırmada eksik modelleri kendi indiriyor; kullanıcıya
   elle dosya indirtmiyor.
8. Hiçbir yerde JSON ayrıştırması yok (ESP32 tarafında).

## 8. İstediğim çıktı

- Yukarıdaki dosya yapısında **tam, derlenen, çalışan** kod.
- İki `README.md`: biri ESP32 için (derleme, flash, ilk kurulum), biri
  sunucu için (kurulum, ffmpeg, Ollama, model indirme, çalıştırma).
- `requirements.txt` ve `kur.sh`.
- `test_istemci.py`.
- Protokolü tek sayfada anlatan `PROTOKOL.md` — başlık düzeni, mesaj
  tipleri, yarı çift yönlü kuralı.

Kodu parça parça değil, **eksiksiz dosyalar hâlinde** ver.
