/* Tepecan - ESP32-S3 istemcisi, ortak ayarlar.
 *
 * Kart: ESP32-S3-DevKitC-1 N16R8 (16 MB flash, 8 MB PSRAM).
 * Ses:  INMP441 (I2S mikrofon) + MAX98357A (I2S amfi).
 *
 * Ağır iş burada değil: ses-metin, dil modeli ve metin-ses ağdaki beyin
 * sunucusunda (yazilim/sunucu/beyin.py) çalışıyor. Bu kartın işi mikrofonu
 * okumak, uyandırma kelimesini yakalamak ve hoparlöre yazmak.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

/* ---------------------------------------------------------------- pinler */
/* TFT yok, bu yüzden S3'ün hemen bütün GPIO'ları serbest. Aşağıdakiler
 * DevKitC-1'de header'a çıkan, açılışta özel anlamı olmayan hatlar. */
#define PIN_MIC_SCK    4        /* INMP441 SCK  (bit clock)   */
#define PIN_MIC_WS     5        /* INMP441 WS   (word select) */
#define PIN_MIC_SD     6        /* INMP441 SD   (veri çıkışı) */

#define PIN_SPK_BCLK   15       /* MAX98357A BCLK */
#define PIN_SPK_LRC    16       /* MAX98357A LRC  */
#define PIN_SPK_DIN    17       /* MAX98357A DIN  */

#define PIN_BUTON      18       /* kapaktaki tactile switch, diğer bacak GND */

/* INMP441'in L/R bacağı GND'ye bağlıysa sol kanaldan konuşur. */
#define MIC_KANAL_SOL  true

/* ----------------------------------------------------------------- ses */
#define ORNEK_HZ       16000    /* STT, VAD ve uyandırma modeli 16 kHz ister */
#define BLOK_ORNEK     320      /* 20 ms - webrtcvad ve mWW ile uyumlu       */
#define EN_UZUN_KAYIT_SN  10    /* bundan sonrası kesiliyor                  */
#define SESSIZLIK_MS   800      /* bu kadar sessizlikten sonra kayıt biter   */

/* ------------------------------------------------------------- uyandırma */
/* Uyandırma kelimesi varsayılan olarak KAPALI. Açmak için:
 *   1. Burayı 1 yap.
 *   2. main/idf_component.yml içindeki üç bağımlılığın yorumunu kaldır.
 *   3. main/CMakeLists.txt'teki REQUIRES satırına "spiffs" ekle.
 *   4. Eğitilmiş modeli "model" bölmesine yükle (bkz. README).
 *
 * Kapalı geliyor çünkü model dosyası olmadan zaten çalışmıyor, ve açıkken
 * derleme kayıt sunucusundan üç bileşen indirmeye çalışıyor. Kapalıyken
 * proje kutudan çıktığı gibi derleniyor; buton tetikleyici olarak yeterli.
 *
 * DİKKAT: uyandirma.cc donanımda denenmedi. microWakeWord'ün beklediği
 * öznitelik çıkarıcı (eski "microfrontend" API'si) güncel esp-tflite-micro
 * sürümlerinde yok, ayrı bir bileşen olarak geliyor - açtığında derleme
 * hatası alırsan ilk bakılacak yer orası.
 */
#define UYANDIRMA_ETKIN 0

/* microWakeWord modeli SPIFFS'te. Dosya yoksa program çalışır, yalnız
 * buton tetikler - uyandırma kelimesi sessizce devre dışı kalır. */
#define WAKE_MODEL_YOLU  "/model/hey_tepecan.tflite"
#define WAKE_ESIK        0.85f  /* 0..1, yükseltmek yanlış tetiklemeyi azaltır */
#define WAKE_ARDISIK     2      /* üst üste kaç pencere eşiği geçmeli          */

/* ------------------------------------------------------------------- ağ */
#define BEYIN_VARSAYILAN "http://tepecan-beyin.local:8000"
#define HTTP_ZAMAN_ASIMI_MS 60000

/* ---------------------------------------------------------------- durum */
typedef enum {
    DURUM_BEKLIYOR,     /* uyandırma kelimesi ya da buton bekleniyor */
    DURUM_DINLIYOR,     /* kayıt sürüyor                             */
    DURUM_DUSUNUYOR,    /* sunucu cevap üretiyor                     */
    DURUM_KONUSUYOR,    /* hoparlör çalıyor                          */
    DURUM_HATA,
} tepecan_durum_t;

void durum_yaz(tepecan_durum_t d);
const char *durum_adi(tepecan_durum_t d);
