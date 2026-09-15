/* microWakeWord çıkarımı.
 *
 * Zincir iki aşamalı: ham ses 10 ms'de bir 40 mel özniteliğine çevriliyor
 * (esp-micro-speech-features), sonra akışlı TFLite modeli her yeni dilimde
 * bir olasılık üretiyor. Model üst üste WAKE_ARDISIK pencere boyunca eşiği
 * geçerse kelime söylenmiş sayılıyor - tek pencereye bakmak çok yanlış
 * tetikliyor.
 *
 * Model dosyası depoda yok, olamaz da: "Hey Tepecan" için kendi modelini
 * eğitmen gerekiyor (bkz. yazilim/esp32/README.md). Dosya yoksa bu modül
 * sessizce kapanıyor ve buton tek tetikleyici olarak kalıyor.
 */
#include "uyandirma.h"
#include "tepecan.h"

#if !UYANDIRMA_ETKIN

/* Kapalı derleme: buton tek tetikleyici. tepecan.h'deki UYANDIRMA_ETKIN
 * 1 yapılınca aşağıdaki gerçek uygulama derleniyor. */
bool uyandirma_baslat(const char *yol) { (void)yol; return false; }
bool uyandirma_acik(void) { return false; }
bool uyandirma_dinle(const int16_t *b, size_t n) { (void)b; (void)n; return false; }
void uyandirma_sifirla(void) {}

#else


#include <cstdio>
#include <cstring>
#include <cstdlib>

#include "esp_log.h"
#include "esp_heap_caps.h"

#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"
#include "microfrontend/lib/frontend.h"
#include "microfrontend/lib/frontend_util.h"

static const char *ETIKET = "uyandirma";

/* microWakeWord'ün eğitimdeki ön işleme ayarları - modelle birebir aynı
 * olmak zorunda, yoksa öznitelikler kayıyor ve model hiç tetiklemiyor. */
static constexpr int OZNITELIK = 40;        /* mel bandı sayısı          */
static constexpr int ADIM_MS   = 10;        /* öznitelik adımı           */
static constexpr int PENCERE_MS = 30;       /* öznitelik penceresi       */
static constexpr size_t ARENA_BOY = 64 * 1024;

static struct FrontendState  g_on;
static struct FrontendConfig g_on_ayar;
static tflite::MicroInterpreter *g_yorum = nullptr;
static TfLiteTensor *g_giris = nullptr;
static uint8_t *g_arena = nullptr;
static uint8_t *g_model = nullptr;
static bool g_acik = false;
static int g_ardisik = 0;

static bool model_oku(const char *yol)
{
    FILE *f = fopen(yol, "rb");
    if (!f) { ESP_LOGW(ETIKET, "model yok: %s", yol); return false; }
    fseek(f, 0, SEEK_END);
    long boy = ftell(f);
    fseek(f, 0, SEEK_SET);
    if (boy <= 0) { fclose(f); return false; }

    g_model = (uint8_t *)heap_caps_malloc(boy, MALLOC_CAP_SPIRAM);
    if (!g_model) { fclose(f); ESP_LOGE(ETIKET, "PSRAM yetmedi"); return false; }
    size_t okundu = fread(g_model, 1, boy, f);
    fclose(f);
    if (okundu != (size_t)boy) { free(g_model); g_model = nullptr; return false; }
    ESP_LOGI(ETIKET, "model yüklendi: %ld bayt", boy);
    return true;
}

bool uyandirma_baslat(const char *model_yolu)
{
    if (!model_oku(model_yolu)) return false;

    /* --- ön işleme --- */
    FrontendFillConfigWithDefaults(&g_on_ayar);
    g_on_ayar.window.size_ms = PENCERE_MS;
    g_on_ayar.window.step_size_ms = ADIM_MS;
    g_on_ayar.filterbank.num_channels = OZNITELIK;
    g_on_ayar.filterbank.lower_band_limit = 125.0f;
    g_on_ayar.filterbank.upper_band_limit = 7500.0f;
    g_on_ayar.noise_reduction.smoothing_bits = 10;
    g_on_ayar.pcan_gain_control.enable_pcan = 1;
    if (!FrontendPopulateState(&g_on_ayar, &g_on, ORNEK_HZ)) {
        ESP_LOGE(ETIKET, "ön işleme kurulamadı");
        return false;
    }

    /* --- model --- */
    const tflite::Model *model = tflite::GetModel(g_model);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        ESP_LOGE(ETIKET, "model şema sürümü uyuşmuyor (%lu)",
                 (unsigned long)model->version());
        return false;
    }

    /* microWakeWord modellerinin kullandığı işlemler. */
    static tflite::MicroMutableOpResolver<8> cozucu;
    cozucu.AddReshape();
    cozucu.AddConv2D();
    cozucu.AddDepthwiseConv2D();
    cozucu.AddFullyConnected();
    cozucu.AddAveragePool2D();
    cozucu.AddLogistic();
    cozucu.AddQuantize();
    cozucu.AddDequantize();

    g_arena = (uint8_t *)heap_caps_malloc(ARENA_BOY, MALLOC_CAP_INTERNAL);
    if (!g_arena) { ESP_LOGE(ETIKET, "arena için iç RAM yetmedi"); return false; }

    static tflite::MicroInterpreter yorum(model, cozucu, g_arena, ARENA_BOY);
    g_yorum = &yorum;
    if (g_yorum->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(ETIKET, "tensörler ayrılamadı - ARENA_BOY yetersiz olabilir");
        return false;
    }
    g_giris = g_yorum->input(0);
    g_acik = true;
    ESP_LOGI(ETIKET, "uyandırma kelimesi hazır (eşik %.2f, %d ardışık)",
             WAKE_ESIK, WAKE_ARDISIK);
    return true;
}

bool uyandirma_acik(void) { return g_acik; }

void uyandirma_sifirla(void)
{
    g_ardisik = 0;
    if (g_acik) FrontendReset(&g_on);
}

bool uyandirma_dinle(const int16_t *blok, size_t ornek)
{
    if (!g_acik) return false;

    size_t kalan = ornek;
    const int16_t *p = blok;

    /* Ön işleme 10 ms'lik dilimler üretiyor; 20 ms'lik blok normalde iki
     * dilim veriyor. Her dilim için modeli bir kez çalıştırıyoruz. */
    while (kalan > 0) {
        size_t islenen = 0;
        struct FrontendOutput cikti =
            FrontendProcessSamples(&g_on, (int16_t *)p, kalan, &islenen);
        if (islenen == 0) break;
        p += islenen;
        kalan -= islenen;
        if (cikti.size == 0) continue;      /* dilim henüz tamamlanmadı */

        /* Öznitelikler int8'e niceleniyor; ölçek modelin kendi giriş
         * niceleme parametrelerinden geliyor. */
        int8_t *giris = tflite::GetTensorData<int8_t>(g_giris);
        const float olcek = g_giris->params.scale;
        const int sifir = g_giris->params.zero_point;
        for (size_t i = 0; i < cikti.size && i < (size_t)OZNITELIK; i++) {
            float v = (float)cikti.values[i];
            int q = (int)(v / (olcek * 25.6f)) + sifir;   /* mWW ölçeği */
            if (q > 127) q = 127;
            if (q < -128) q = -128;
            giris[i] = (int8_t)q;
        }

        if (g_yorum->Invoke() != kTfLiteOk) continue;

        TfLiteTensor *cik = g_yorum->output(0);
        float olasilik;
        if (cik->type == kTfLiteInt8) {
            int8_t ham = tflite::GetTensorData<int8_t>(cik)[0];
            olasilik = (ham - cik->params.zero_point) * cik->params.scale;
        } else {
            olasilik = tflite::GetTensorData<float>(cik)[0];
        }

        if (olasilik >= WAKE_ESIK) {
            if (++g_ardisik >= WAKE_ARDISIK) {
                ESP_LOGI(ETIKET, "kelime duyuldu (%.2f)", olasilik);
                uyandirma_sifirla();
                return true;
            }
        } else {
            g_ardisik = 0;
        }
    }
    return false;
}

#endif /* UYANDIRMA_ETKIN */
