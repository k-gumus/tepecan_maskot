/* I2S mikrofon (INMP441) ve hoparlör (MAX98357A). */
#pragma once

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

esp_err_t ses_baslat(void);

/* BLOK_ORNEK kadar 16-bit mono örnek okur. Bloklar. */
esp_err_t mik_oku(int16_t *hedef, size_t ornek);

/* Mikrofonu durdurur/başlatır. Çalarken durdurmak üç işi birden çözüyor:
 * Tepecan kendi sesini duymuyor, aynı anda hem giriş hem çıkış istenmiyor,
 * ve tampon boşuna dolmuyor. */
void mik_duraklat(void);
void mik_devam(void);
void mik_bosalt(void);

/* Ham 16-bit mono PCM çalar. */
esp_err_t hoparlor_cal(const int16_t *pcm, size_t ornek, uint32_t hz);

/* Bir bloğun konuşma sayılacak kadar yüksek olup olmadığı (basit enerji
 * eşiği). webrtcvad ESP32'de yok; RMS pratikte yeterli çünkü asıl kesme
 * kararını sunucudaki whisper'ın vad_filter'ı zaten bir kez daha veriyor. */
bool ses_var_mi(const int16_t *blok, size_t ornek);
