/* WiFi bağlantısı ve beyin sunucusu istemcisi. */
#pragma once

#include <stddef.h>
#include <stdbool.h>
#include <stdint.h>
#include "esp_err.h"

/* NVS'teki bilgilerle bağlanır. Kayıt yoksa ya da bağlanamazsa kendi
 * erişim noktasını açar ("Tepecan-Kurulum"), telefondan ağ seçtirir ve
 * kaydeder. Yani ilk yüklemeden sonra bilgisayara bir daha gerek yok. */
esp_err_t ag_baslat(void);
bool ag_bagli(void);

/* portal.c / ag.c arasinda paylasilan yardimcilar */
esp_err_t kurulum_noktasi_ac(void);
esp_err_t nvs_yaz(const char *anahtar, const char *deger);

/* Beyin sunucusunun adresi (NVS'te saklanır, kurulum sayfasından girilir). */
const char *beyin_adresi(void);

/* WAV gönder, Türkçe metin al. Dönen metin çağıranın free'leyeceği bir
 * tamponda; hata olursa NULL. */
char *beyin_stt(const uint8_t *wav, size_t uzunluk);

/* Soruyu gönder, cevabı al. Ollama'yı ve cümlelere bölmeyi sunucu yapıyor;
 * mikrodenetleyiciye akan JSON ayrıştırmak gereksiz eziyet. */
char *beyin_chat(const char *soru);

/* Metni seslendir. WAV'ı PSRAM'de döndürür; çağıran free'ler. */
uint8_t *beyin_tts(const char *metin, size_t *uzunluk);
