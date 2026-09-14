#include "ses.h"
#include "tepecan.h"

#include <string.h>
#include <math.h>
#include "driver/i2s_std.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

static const char *ETIKET = "ses";

static i2s_chan_handle_t mik_kanal;
static i2s_chan_handle_t hop_kanal;
static bool mik_acik;

/* INMP441 24 bitlik veriyi 32 bitlik yuvada gönderiyor; 32 bit okuyup
 * yukarı hizalanmış 16 biti alıyoruz. */
#define MIK_YUVA I2S_DATA_BIT_WIDTH_32BIT

static esp_err_t mikrofon_kur(void)
{
    i2s_chan_config_t kanal = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_0, I2S_ROLE_MASTER);
    kanal.dma_desc_num = 6;
    kanal.dma_frame_num = BLOK_ORNEK;
    kanal.auto_clear = true;
    ESP_ERROR_CHECK(i2s_new_channel(&kanal, NULL, &mik_kanal));

    i2s_std_config_t std = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(ORNEK_HZ),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
            MIK_YUVA, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = PIN_MIC_SCK,
            .ws   = PIN_MIC_WS,
            .dout = I2S_GPIO_UNUSED,
            .din  = PIN_MIC_SD,
            .invert_flags = { false, false, false },
        },
    };
    std.slot_cfg.slot_mask = MIC_KANAL_SOL ? I2S_STD_SLOT_LEFT : I2S_STD_SLOT_RIGHT;
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(mik_kanal, &std));
    ESP_ERROR_CHECK(i2s_channel_enable(mik_kanal));
    mik_acik = true;
    return ESP_OK;
}

static esp_err_t hoparlor_kur(void)
{
    i2s_chan_config_t kanal = I2S_CHANNEL_DEFAULT_CONFIG(I2S_NUM_1, I2S_ROLE_MASTER);
    kanal.dma_desc_num = 8;
    kanal.dma_frame_num = 240;
    kanal.auto_clear = true;
    ESP_ERROR_CHECK(i2s_new_channel(&kanal, &hop_kanal, NULL));

    i2s_std_config_t std = {
        .clk_cfg = I2S_STD_CLK_DEFAULT_CONFIG(ORNEK_HZ),
        .slot_cfg = I2S_STD_PHILIPS_SLOT_DEFAULT_CONFIG(
            I2S_DATA_BIT_WIDTH_16BIT, I2S_SLOT_MODE_MONO),
        .gpio_cfg = {
            .mclk = I2S_GPIO_UNUSED,
            .bclk = PIN_SPK_BCLK,
            .ws   = PIN_SPK_LRC,
            .dout = PIN_SPK_DIN,
            .din  = I2S_GPIO_UNUSED,
            .invert_flags = { false, false, false },
        },
    };
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(hop_kanal, &std));
    return ESP_OK;
}

esp_err_t ses_baslat(void)
{
    ESP_ERROR_CHECK(mikrofon_kur());
    ESP_ERROR_CHECK(hoparlor_kur());
    ESP_LOGI(ETIKET, "I2S hazır: mik %d/%d/%d, hoparlör %d/%d/%d",
             PIN_MIC_SCK, PIN_MIC_WS, PIN_MIC_SD,
             PIN_SPK_BCLK, PIN_SPK_LRC, PIN_SPK_DIN);
    return ESP_OK;
}

esp_err_t mik_oku(int16_t *hedef, size_t ornek)
{
    static int32_t ham[BLOK_ORNEK];
    size_t okundu = 0;
    if (ornek > BLOK_ORNEK) ornek = BLOK_ORNEK;

    esp_err_t r = i2s_channel_read(mik_kanal, ham, ornek * sizeof(int32_t),
                                   &okundu, portMAX_DELAY);
    if (r != ESP_OK) return r;

    size_t n = okundu / sizeof(int32_t);
    for (size_t i = 0; i < n; i++) {
        /* INMP441: anlamlı 24 bit üstte. 16 bite indirmek için 11 kaydırıp
         * (8 bit hizalama + 3 bit kazanç) taşmaya karşı kırpıyoruz. */
        int32_t v = ham[i] >> 11;
        if (v > 32767) v = 32767;
        if (v < -32768) v = -32768;
        hedef[i] = (int16_t)v;
    }
    for (size_t i = n; i < ornek; i++) hedef[i] = 0;
    return ESP_OK;
}

void mik_duraklat(void)
{
    if (mik_acik) { i2s_channel_disable(mik_kanal); mik_acik = false; }
}

void mik_devam(void)
{
    if (!mik_acik) { i2s_channel_enable(mik_kanal); mik_acik = true; }
}

void mik_bosalt(void)
{
    /* Tetikten önce biriken sesi at, yoksa kayıt eski gürültüyle başlıyor. */
    static int16_t cop[BLOK_ORNEK];
    for (int i = 0; i < 8; i++) mik_oku(cop, BLOK_ORNEK);
}

esp_err_t hoparlor_cal(const int16_t *pcm, size_t ornek, uint32_t hz)
{
    /* Sunucudan gelen WAV 22.05 kHz olabiliyor (Piper), mikrofon 16 kHz.
     * Kanalı çalmadan önce o hıza ayarlıyoruz. */
    i2s_std_clk_config_t saat = I2S_STD_CLK_DEFAULT_CONFIG(hz);
    ESP_ERROR_CHECK(i2s_channel_disable(hop_kanal));
    ESP_ERROR_CHECK(i2s_channel_reconfig_std_clock(hop_kanal, &saat));
    ESP_ERROR_CHECK(i2s_channel_enable(hop_kanal));

    size_t yazildi = 0;
    esp_err_t r = i2s_channel_write(hop_kanal, pcm, ornek * sizeof(int16_t),
                                    &yazildi, portMAX_DELAY);
    /* Son tamponun gerçekten çıkması için kısa bir bekleme; hemen disable
     * edersek cümlenin sonu kesiliyor. */
    vTaskDelay(pdMS_TO_TICKS(60));
    i2s_channel_disable(hop_kanal);
    return r;
}

bool ses_var_mi(const int16_t *blok, size_t ornek)
{
    int64_t kare = 0;
    for (size_t i = 0; i < ornek; i++) kare += (int32_t)blok[i] * blok[i];
    double rms = sqrt((double)kare / (double)ornek);
    return rms > 500.0;          /* sessiz oda ~100-200, konuşma >1000 */
}
