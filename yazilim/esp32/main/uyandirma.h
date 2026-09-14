/* microWakeWord ile cihaz üstünde uyandırma kelimesi. */
#pragma once

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/* Modeli SPIFFS'ten yükler. Dosya yoksa false döner - program yine çalışır,
 * yalnız buton tetikler. */
bool uyandirma_baslat(const char *model_yolu);
bool uyandirma_acik(void);

/* 20 ms'lik bir blok ver; kelime duyulduysa true. */
bool uyandirma_dinle(const int16_t *blok, size_t ornek);

/* Tetikten sonra durumu sıfırla, yoksa aynı kelime tekrar tetikliyor. */
void uyandirma_sifirla(void);

#ifdef __cplusplus
}
#endif
