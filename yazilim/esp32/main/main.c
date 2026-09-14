/* Tepecan - ESP32-S3 istemcisi.
 *
 *   uyandırma kelimesi ya da buton
 *      -> kayıt (sen susunca biter)
 *      -> /stt-raw  (ses  -> metin)
 *      -> /chat     (metin -> cevap)
 *      -> /tts      (cevap -> ses)
 *      -> hoparlör
 *
 * Bütün ağır iş beyin sunucusunda. Burada yalnız akış ve zamanlama var.
 */
#include "tepecan.h"
#include "ses.h"
#include "ag.h"
#include "uyandirma.h"

#include <string.h>
#include <stdlib.h>
#include "driver/gpio.h"
#include "esp_log.h"
#include "esp_heap_caps.h"
#include "esp_spiffs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *ETIKET = "tepecan";
static tepecan_durum_t g_durum = DURUM_BEKLIYOR;

const char *durum_adi(tepecan_durum_t d)
{
    switch (d) {
    case DURUM_BEKLIYOR:  return "bekliyor";
    case DURUM_DINLIYOR:  return "dinliyor";
    case DURUM_DUSUNUYOR: return "düşünüyor";
    case DURUM_KONUSUYOR: return "konuşuyor";
    default:              return "hata";
    }
}

void durum_yaz(tepecan_durum_t d)
{
    if (d == g_durum) return;
    g_durum = d;
    ESP_LOGI(ETIKET, "durum: %s", durum_adi(d));
}

/* ------------------------------------------------------------------ WAV */
/* 44 baytlık standart başlık; whisper tarafında sorunsuz açılıyor. */
static void wav_basligi(uint8_t *b, uint32_t veri_boy, uint32_t hz)
{
    uint32_t bayt_hz = hz * 2;
    memcpy(b, "RIFF", 4);
    uint32_t riff = 36 + veri_boy;   memcpy(b + 4, &riff, 4);
    memcpy(b + 8, "WAVEfmt ", 8);
    uint32_t fmt = 16;               memcpy(b + 16, &fmt, 4);
    uint16_t pcm = 1, kanal = 1;     memcpy(b + 20, &pcm, 2); memcpy(b + 22, &kanal, 2);
    memcpy(b + 24, &hz, 4);
    memcpy(b + 28, &bayt_hz, 4);
    uint16_t hiza = 2, bit = 16;     memcpy(b + 32, &hiza, 2); memcpy(b + 34, &bit, 2);
    memcpy(b + 36, "data", 4);       memcpy(b + 40, &veri_boy, 4);
}

/* Gelen WAV'ın veri bölümünü ve örnekleme hızını bul. */
static const int16_t *wav_coz(const uint8_t *wav, size_t boy,
                              size_t *ornek, uint32_t *hz)
{
    if (boy < 44 || memcmp(wav, "RIFF", 4) != 0) return NULL;
    memcpy(hz, wav + 24, 4);
    size_t p = 12;
    while (p + 8 <= boy) {
        uint32_t parca_boy;
        memcpy(&parca_boy, wav + p + 4, 4);
        if (memcmp(wav + p, "data", 4) == 0) {
            if (p + 8 + parca_boy > boy) parca_boy = boy - p - 8;
            *ornek = parca_boy / 2;
            return (const int16_t *)(wav + p + 8);
        }
        p += 8 + parca_boy + (parca_boy & 1);
    }
    return NULL;
}

/* ---------------------------------------------------------------- buton */
static void buton_kur(void)
{
    gpio_config_t c = {
        .pin_bit_mask = 1ULL << PIN_BUTON,
        .mode = GPIO_MODE_INPUT,
        .pull_up_en = GPIO_PULLUP_ENABLE,
        .pull_down_en = GPIO_PULLDOWN_DISABLE,
        .intr_type = GPIO_INTR_DISABLE,
    };
    gpio_config(&c);
}

static bool buton_basili(void) { return gpio_get_level(PIN_BUTON) == 0; }

/* ---------------------------------------------------------------- akış */
/* Tetik gelene kadar dinler. Dönen değer: "buton" ya da "kelime". */
static const char *tetik_bekle(void)
{
    static int16_t blok[BLOK_ORNEK];
    uyandirma_sifirla();
    while (true) {
        if (mik_oku(blok, BLOK_ORNEK) != ESP_OK) continue;

        if (buton_basili()) {
            while (buton_basili()) vTaskDelay(pdMS_TO_TICKS(20));
            return "buton";
        }
        if (uyandirma_dinle(blok, BLOK_ORNEK)) return "kelime";
    }
}

/* Sen susana kadar kaydeder. WAV'ı PSRAM'de döndürür. */
static uint8_t *sessizlige_kadar_kaydet(size_t *wav_boy)
{
    const size_t en_cok = (size_t)ORNEK_HZ * EN_UZUN_KAYIT_SN;
    uint8_t *wav = heap_caps_malloc(44 + en_cok * 2, MALLOC_CAP_SPIRAM);
    if (!wav) { ESP_LOGE(ETIKET, "kayıt için PSRAM yetmedi"); return NULL; }

    int16_t *veri = (int16_t *)(wav + 44);
    size_t yazilan = 0;
    int sessiz_blok = 0;
    const int sessiz_sinir = SESSIZLIK_MS / (BLOK_ORNEK * 1000 / ORNEK_HZ);
    bool konusma_basladi = false;

    while (yazilan + BLOK_ORNEK <= en_cok) {
        if (mik_oku(veri + yazilan, BLOK_ORNEK) != ESP_OK) break;
        bool ses = ses_var_mi(veri + yazilan, BLOK_ORNEK);
        yazilan += BLOK_ORNEK;

        if (ses) { konusma_basladi = true; sessiz_blok = 0; }
        else if (konusma_basladi && ++sessiz_blok >= sessiz_sinir) break;
        /* Hiç konuşma başlamadıysa 3 saniye sonra vazgeç. */
        else if (!konusma_basladi && yazilan > (size_t)ORNEK_HZ * 3) {
            free(wav);
            return NULL;
        }
    }
    if (!konusma_basladi) { free(wav); return NULL; }

    wav_basligi(wav, yazilan * 2, ORNEK_HZ);
    *wav_boy = 44 + yazilan * 2;
    ESP_LOGI(ETIKET, "kayıt bitti: %.1f sn", (float)yazilan / ORNEK_HZ);
    return wav;
}

static void konus(const char *metin)
{
    size_t wav_boy = 0;
    uint8_t *wav = beyin_tts(metin, &wav_boy);
    if (!wav) return;

    size_t ornek = 0;
    uint32_t hz = ORNEK_HZ;
    const int16_t *pcm = wav_coz(wav, wav_boy, &ornek, &hz);
    if (pcm) {
        durum_yaz(DURUM_KONUSUYOR);
        hoparlor_cal(pcm, ornek, hz);
    }
    free(wav);
}

static void tur(void)
{
    durum_yaz(DURUM_BEKLIYOR);
    mik_bosalt();
    const char *nasil = tetik_bekle();
    ESP_LOGI(ETIKET, "(%s ile uyandı)", nasil);

    durum_yaz(DURUM_DINLIYOR);
    size_t wav_boy = 0;
    uint8_t *wav = sessizlige_kadar_kaydet(&wav_boy);
    if (!wav) return;

    /* Bundan sonrası mikrofonu gerektirmiyor. Kapatmak Tepecan'ın kendi
     * sesini duymasını da engelliyor. */
    mik_duraklat();
    durum_yaz(DURUM_DUSUNUYOR);

    char *soru = beyin_stt(wav, wav_boy);
    free(wav);
    if (!soru || soru[0] == '\0') {
        free(soru);
        mik_devam();
        return;
    }
    ESP_LOGI(ETIKET, "sen: %s", soru);

    char *cevap = beyin_chat(soru);
    free(soru);
    if (cevap) {
        ESP_LOGI(ETIKET, "tepecan: %s", cevap);
        konus(cevap);
        free(cevap);
    }
    mik_devam();
}

/* ----------------------------------------------------------------- giriş */
static void spiffs_bagla(void)
{
    esp_vfs_spiffs_conf_t c = {
        .base_path = "/model",
        .partition_label = "model",
        .max_files = 2,
        .format_if_mount_failed = true,
    };
    esp_err_t r = esp_vfs_spiffs_register(&c);
    if (r != ESP_OK) ESP_LOGW(ETIKET, "SPIFFS bağlanamadı: %s", esp_err_to_name(r));
}

void app_main(void)
{
    ESP_LOGI(ETIKET, "Tepecan başlıyor");
    buton_kur();
    spiffs_bagla();
    ESP_ERROR_CHECK(ses_baslat());

    esp_err_t r = ag_baslat();
    if (r == ESP_ERR_NOT_FINISHED) {
        /* Kurulum portalı açık; kullanıcı ağ bilgisini girince kart kendi
         * yeniden başlıyor. Burada beklemekten başka yapacak iş yok. */
        while (true) vTaskDelay(pdMS_TO_TICKS(1000));
    }
    if (r != ESP_OK) ESP_LOGW(ETIKET, "ağa bağlanılamadı, denemeye devam");

    if (!uyandirma_baslat(WAKE_MODEL_YOLU))
        ESP_LOGW(ETIKET, "uyandırma kelimesi kapalı - yalnız buton tetikler");

    ESP_LOGI(ETIKET, "hazır. beyin: %s", beyin_adresi());
    while (true) tur();
}
