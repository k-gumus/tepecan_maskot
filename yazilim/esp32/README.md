# Tepecan — ESP32-S3 istemcisi

Maskotun içindeki kart. Mikrofonu dinler, uyandırma kelimesini yakalar,
beyin sunucusuna gönderir, gelen cevabı hoparlörden çalar. Ses-metin, dil
modeli ve metin-ses bu kartta değil — hepsi `yazilim/sunucu/beyin.py`'de.

**Donanım:** ESP32-S3-DevKitC-1 N16R8 (16 MB flash, 8 MB PSRAM) ·
INMP441 I2S mikrofon · MAX98357A I2S amfi · Ø30 mm 4 Ω hoparlör ·
6×6 mm tactile switch.

PSRAM şart: kayıt tamponu ve Piper'dan gelen WAV orada duruyor.

## Bağlantılar

| Modül | Bacak | ESP32-S3 |
|---|---|---|
| INMP441 | VDD | 3V3 |
| | GND, L/R | GND |
| | SCK | GPIO4 |
| | WS | GPIO5 |
| | SD | GPIO6 |
| MAX98357A | VIN | **5V** (3V3 değil) |
| | GND | GND |
| | BCLK | GPIO15 |
| | LRC | GPIO16 |
| | DIN | GPIO17 |
| Buton | bacak 1 | GPIO18 |
| | bacak 2 | GND |
| Hoparlör | +/− | MAX98357A çıkışı |

INMP441'in **L/R bacağı GND'ye** gitmeli — sol kanaldan konuşsun diye;
kod da sol kanalı okuyor. Pinleri değiştirmek istersen `main/tepecan.h`.

## Derleme ve yükleme

ESP-IDF v5.1 veya üstü gerekiyor; v5.3 ve v6.1 ile derlendiği doğrulandı.

```bash
idf.py set-target esp32s3
idf.py build
idf.py -p /dev/ttyUSB0 flash monitor
```

> DevKitC-1'de **iki USB-C portu** var (biri native USB, biri UART).
> Yükleme olmazsa diğerini dene — en çok takılınan yer burası.

Windows'ta projeyi **ASCII bir yola** koy (`C:\esp\tepecan` gibi): ESP-IDF
Türkçe karakterli yollarda (`Masaüstü`) takılıyor, OneDrive içinde derlemek de
dosya kilidi sorunları çıkarıyor.

Bağımlılıklar (`esp-tflite-micro`, `esp-nn`, `esp-micro-speech-features`)
`main/idf_component.yml` ile otomatik iniyor, elle bir şey kurmana gerek yok.

## İlk kurulum — bilgisayara gerek yok

Wi-Fi bilgisi koda gömülü değil. Kart kayıtlı ağ bulamazsa kendi erişim
noktasını açıyor:

1. Telefondan **`Tepecan-Kurulum`** ağına bağlan (şifresiz).
2. Tarayıcıda `http://192.168.4.1` aç.
3. Wi-Fi adı, şifresi ve beyin sunucusunun adresini gir.
4. Kaydet — kart yeniden başlayıp o ağa bağlanıyor.

Bilgiler NVS'e yazılıyor, sonraki açılışlarda kendi bağlanıyor. Kulüpten
etkinliğe geçerken ağ değiştirmek için de aynı portal yeter; USB yalnız
ilk yüklemede lazım.

## Uyandırma kelimesi

"Hey Tepecan" modeli depoda **yok**, olamaz da: microWakeWord modelleri
söylenen ifadeye özel eğitiliyor. Kart model dosyası olmadan da çalışır —
o zaman yalnız sırt kapağındaki buton tetikler.

Model eğitmek için:

1. <https://microwakeword.com/train> üzerinden "Hey Tepecan" ifadesini
   eğit (Colab defteri, ücretsiz GPU ile birkaç saat).
2. Çıkan `.tflite` dosyasını `hey_tepecan.tflite` diye adlandır.
3. `model` bölümüne yükle:
   ```bash
   mkdir -p spiffs && cp hey_tepecan.tflite spiffs/
   idf.py storage-flash        # ya da: parttool.py write_partition --partition-name=model
   ```

Dürüst uyarı: microWakeWord'ün kendi belgeleri *"iyi çalışan bir model
eğitmek hâlâ çok zor, ileri seviye kullanıcılar için"* diyor. İlk denemede
tutmayabilir. Yanlış tetikleme çoksa `tepecan.h` içinde `WAKE_ESIK`'i
yükselt (0.85 → 0.92) ya da `WAKE_ARDISIK`'ı 3 yap; hiç tetiklemiyorsa tersi.

Hazır bir modelle zinciri denemek istersen
<https://microwakeword.com/library> altında topluluk modelleri var.

## Ayarlar

Hepsi `main/tepecan.h` içinde: pinler, örnekleme hızı, sessizlik eşiği,
uyandırma eşiği, varsayılan sunucu adresi.

`main/ses.c` içindeki `ses_var_mi()` basit bir RMS eşiği (500) kullanıyor.
Oda gürültülüyse kayıt hiç bitmiyor olabilir — eşiği yükselt. Çok sessizse
ve kayıt erken kesiliyorsa düşür.

## Bilinmesi gerekenler

- **Bu kod donanım üzerinde denenmedi.** Elimde kart yokken yazıldı;
  ilk yüklemede I2S pin/kanal ayarlarında düzeltme gerekebilir. En olası
  yer: INMP441'in kanal seçimi (`MIC_KANAL_SOL`) ve kazanç kaydırması
  (`ses.c` içinde `>> 11`) — ses çok kısık ya da bozuk gelirse orası.
- Beyin sunucusu açık olmalı. Kart ona ulaşamazsa duyar ama cevap veremez.
- MAX98357A pille çalışırken 5 V yerine 3.7-4.2 V görür, ses biraz kısılır.
