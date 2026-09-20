#include "ag.h"
#include "tepecan.h"

#include <string.h>
#include <stdlib.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "esp_http_client.h"
#include "esp_heap_caps.h"
#include "nvs_flash.h"
#include "nvs.h"
#include "freertos/FreeRTOS.h"
#include "freertos/event_groups.h"

static const char *ETIKET = "ag";
static EventGroupHandle_t olaylar;
#define BIT_BAGLANDI BIT0
static char g_beyin[128] = BEYIN_VARSAYILAN;
static bool g_bagli;

/* ------------------------------------------------------------------ NVS */
static esp_err_t nvs_oku(const char *anahtar, char *hedef, size_t boy)
{
    nvs_handle_t h;
    if (nvs_open("tepecan", NVS_READONLY, &h) != ESP_OK) return ESP_FAIL;
    esp_err_t r = nvs_get_str(h, anahtar, hedef, &boy);
    nvs_close(h);
    return r;
}

esp_err_t nvs_yaz(const char *anahtar, const char *deger)
{
    nvs_handle_t h;
    if (nvs_open("tepecan", NVS_READWRITE, &h) != ESP_OK) return ESP_FAIL;
    esp_err_t r = nvs_set_str(h, anahtar, deger);
    if (r == ESP_OK) r = nvs_commit(h);
    nvs_close(h);
    return r;
}

/* --------------------------------------------------------------- olaylar */
static void olay(void *arg, esp_event_base_t taban, int32_t id, void *veri)
{
    if (taban == WIFI_EVENT && id == WIFI_EVENT_STA_START) {
        esp_wifi_connect();
    } else if (taban == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        g_bagli = false;
        xEventGroupClearBits(olaylar, BIT_BAGLANDI);
        ESP_LOGW(ETIKET, "bağlantı koptu, yeniden deneniyor");
        vTaskDelay(pdMS_TO_TICKS(2000));
        esp_wifi_connect();
    } else if (taban == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *e = veri;
        ESP_LOGI(ETIKET, "IP: " IPSTR, IP2STR(&e->ip_info.ip));
        g_bagli = true;
        xEventGroupSetBits(olaylar, BIT_BAGLANDI);
    }
}

esp_err_t ag_baslat(void)
{
    esp_err_t r = nvs_flash_init();
    if (r == ESP_ERR_NVS_NO_FREE_PAGES || r == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        ESP_ERROR_CHECK(nvs_flash_erase());
        ESP_ERROR_CHECK(nvs_flash_init());
    }
    nvs_oku("beyin", g_beyin, sizeof(g_beyin));

    char ssid[33] = {0}, sifre[65] = {0};
    if (nvs_oku("ssid", ssid, sizeof(ssid)) != ESP_OK || ssid[0] == '\0') {
        ESP_LOGW(ETIKET, "kayıtlı ağ yok - kurulum noktası açılıyor");
        return kurulum_noktasi_ac();       /* portal.c */
    }
    nvs_oku("sifre", sifre, sizeof(sifre));

    olaylar = xEventGroupCreate();
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_sta();

    wifi_init_config_t ayar = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&ayar));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        WIFI_EVENT, ESP_EVENT_ANY_ID, &olay, NULL, NULL));
    ESP_ERROR_CHECK(esp_event_handler_instance_register(
        IP_EVENT, IP_EVENT_STA_GOT_IP, &olay, NULL, NULL));

    wifi_config_t wc = { 0 };
    strncpy((char *)wc.sta.ssid, ssid, sizeof(wc.sta.ssid));
    strncpy((char *)wc.sta.password, sifre, sizeof(wc.sta.password));
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wc));
    ESP_ERROR_CHECK(esp_wifi_start());

    ESP_LOGI(ETIKET, "'%s' ağına bağlanılıyor, beyin: %s", ssid, g_beyin);
    xEventGroupWaitBits(olaylar, BIT_BAGLANDI, pdFALSE, pdTRUE,
                        pdMS_TO_TICKS(30000));
    return g_bagli ? ESP_OK : ESP_ERR_TIMEOUT;
}

bool ag_bagli(void) { return g_bagli; }
const char *beyin_adresi(void) { return g_beyin; }

/* ------------------------------------------------------------ HTTP yardım */
typedef struct { char *veri; size_t boy; size_t sinir; } tampon_t;

static esp_err_t topla(esp_http_client_event_t *e)
{
    tampon_t *t = e->user_data;
    if (e->event_id != HTTP_EVENT_ON_DATA || !t) return ESP_OK;
    if (t->boy + e->data_len + 1 > t->sinir) return ESP_OK;   /* taşma koruması */
    memcpy(t->veri + t->boy, e->data, e->data_len);
    t->boy += e->data_len;
    t->veri[t->boy] = '\0';
    return ESP_OK;
}

static char *gonder(const char *yol, const char *tur,
                    const void *govde, size_t govde_boy, size_t sinir,
                    size_t *gelen_boy)
{
    char url[192];
    snprintf(url, sizeof(url), "%s%s", g_beyin, yol);

    char *cikti = heap_caps_malloc(sinir, MALLOC_CAP_SPIRAM);
    if (!cikti) { ESP_LOGE(ETIKET, "PSRAM yetmedi (%u)", (unsigned)sinir); return NULL; }
    cikti[0] = '\0';
    tampon_t t = { .veri = cikti, .boy = 0, .sinir = sinir };

    esp_http_client_config_t ayar = {
        .url = url,
        .method = HTTP_METHOD_POST,
        .timeout_ms = HTTP_ZAMAN_ASIMI_MS,
        .event_handler = topla,
        .user_data = &t,
        .buffer_size = 2048,
    };
    esp_http_client_handle_t c = esp_http_client_init(&ayar);
    esp_http_client_set_header(c, "Content-Type", tur);
    esp_http_client_set_post_field(c, (const char *)govde, govde_boy);

    esp_err_t r = esp_http_client_perform(c);
    int kod = esp_http_client_get_status_code(c);
    esp_http_client_cleanup(c);

    if (r != ESP_OK || kod != 200) {
        ESP_LOGE(ETIKET, "%s başarısız (%s, HTTP %d)", yol, esp_err_to_name(r), kod);
        free(cikti);
        return NULL;
    }
    t.veri[t.boy] = '\0';
    if (gelen_boy) *gelen_boy = t.boy;
    return cikti;
}

/* ----------------------------------------------------------------- JSON
 * Eskiden cJSON kullanıyorduk, yani ESP-IDF'in "json" bileşenine. O bileşen
 * v6'da çekirdekten çıkarıldı ve kurulum "Failed to resolve component 'json'"
 * diye çöküyordu. İhtiyacımız iki şeyle sınırlı -- üst düzey bir metin alanı
 * okumak ve {"text": "..."} kurmak -- o yüzden ikisi burada. Bağımlılık
 * kalmadığı için hangi IDF sürümünde olursa olsun derleniyor.
 */
static size_t utf8_yaz(char *hedef, unsigned kod)
{
    if (kod < 0x80)   { hedef[0] = (char)kod; return 1; }
    if (kod < 0x800)  { hedef[0] = (char)(0xC0 | (kod >> 6));
                        hedef[1] = (char)(0x80 | (kod & 0x3F)); return 2; }
    if (kod < 0x10000){ hedef[0] = (char)(0xE0 | (kod >> 12));
                        hedef[1] = (char)(0x80 | ((kod >> 6) & 0x3F));
                        hedef[2] = (char)(0x80 | (kod & 0x3F)); return 3; }
    hedef[0] = (char)(0xF0 | (kod >> 18));
    hedef[1] = (char)(0x80 | ((kod >> 12) & 0x3F));
    hedef[2] = (char)(0x80 | ((kod >> 6) & 0x3F));
    hedef[3] = (char)(0x80 | (kod & 0x3F));
    return 4;
}

static unsigned onalti4(const char *s)
{
    unsigned v = 0;
    for (int i = 0; i < 4; i++) {
        char c = s[i];
        v <<= 4;
        if      (c >= '0' && c <= '9') v |= (unsigned)(c - '0');
        else if (c >= 'a' && c <= 'f') v |= (unsigned)(c - 'a' + 10);
        else if (c >= 'A' && c <= 'F') v |= (unsigned)(c - 'A' + 10);
        else return 0xFFFFFFFFu;
    }
    return v;
}

/* Açılış tırnağından sonrasını alır, kapanış tırnağının ardını döndürür. */
static const char *dizge_atla(const char *p)
{
    while (*p) {
        if (*p == '\\' && p[1]) { p += 2; continue; }
        if (*p == '"') return p + 1;
        p++;
    }
    return p;
}

/* Açılış tırnağından sonrasını alır, kaçışları çözüp yeni tampon döndürür.
 * Çözülen metin kaynaktan uzun olamaz: en uzun kaçış (\uXXXX, 6 karakter)
 * en çok 4 bayt üretiyor. */
static char *dizge_coz(const char *p)
{
    char *cikti = malloc(strlen(p) + 1);
    if (!cikti) return NULL;
    size_t n = 0;
    while (*p && *p != '"') {
        if (*p != '\\') { cikti[n++] = *p++; continue; }
        p++;
        switch (*p) {
        case 'n': cikti[n++] = '\n'; p++; break;
        case 't': cikti[n++] = '\t'; p++; break;
        case 'r': cikti[n++] = '\r'; p++; break;
        case 'b': cikti[n++] = '\b'; p++; break;
        case 'f': cikti[n++] = '\f'; p++; break;
        case 'u': {
            unsigned kod = onalti4(p + 1);
            if (kod == 0xFFFFFFFFu) { free(cikti); return NULL; }
            p += 5;
            if (kod >= 0xD800 && kod <= 0xDBFF && p[0] == '\\' && p[1] == 'u') {
                unsigned alt = onalti4(p + 2);
                if (alt >= 0xDC00 && alt <= 0xDFFF) {
                    kod = 0x10000u + ((kod - 0xD800u) << 10) + (alt - 0xDC00u);
                    p += 6;
                }
            }
            n += utf8_yaz(cikti + n, kod);
            break;
        }
        case '\0': free(cikti); return NULL;
        default: cikti[n++] = *p++; break;          /* \" \\ \/ */
        }
    }
    cikti[n] = '\0';
    return cikti;
}

/* Üst düzey bir metin alanını çek. Değerlerin içindeki tırnaklara takılmamak
 * için dizgeler bütün hâlde atlanıyor. */
static char *json_metin_alani(const char *json, const char *ad)
{
    size_t adboy = strlen(ad);
    const char *p = json;
    while (*p) {
        if (*p != '"') { p++; continue; }
        const char *anahtar = p + 1;
        const char *son = dizge_atla(anahtar);       /* kapanış tırnağının ardı */
        const char *q = son;
        while (*q == ' ' || *q == '\t' || *q == '\n' || *q == '\r') q++;
        if (*q == ':') {
            bool esles = (size_t)(son - 1 - anahtar) == adboy &&
                         strncmp(anahtar, ad, adboy) == 0;
            q++;
            while (*q == ' ' || *q == '\t' || *q == '\n' || *q == '\r') q++;
            if (esles) return (*q == '"') ? dizge_coz(q + 1) : NULL;
            if (*q == '"') { p = dizge_atla(q + 1); continue; }
        }
        p = son;
    }
    return NULL;
}

/* {"ad":"deger"} kurar. Her karakter en çok 6 karaktere (\u00XX) açılıyor. */
static char *json_metin_govdesi(const char *ad, const char *deger)
{
    size_t kapasite = strlen(ad) + strlen(deger) * 6 + 16;
    char *cikti = malloc(kapasite);
    if (!cikti) return NULL;
    size_t n = (size_t)snprintf(cikti, kapasite, "{\"%s\":\"", ad);
    for (const unsigned char *s = (const unsigned char *)deger; *s; s++) {
        if      (*s == '"' || *s == '\\') { cikti[n++] = '\\'; cikti[n++] = (char)*s; }
        else if (*s == '\n') { cikti[n++] = '\\'; cikti[n++] = 'n'; }
        else if (*s == '\r') { cikti[n++] = '\\'; cikti[n++] = 'r'; }
        else if (*s == '\t') { cikti[n++] = '\\'; cikti[n++] = 't'; }
        else if (*s < 0x20)  { n += (size_t)snprintf(cikti + n, kapasite - n,
                                                     "\\u%04x", (unsigned)*s); }
        else cikti[n++] = (char)*s;
    }
    cikti[n++] = '"';
    cikti[n++] = '}';
    cikti[n] = '\0';
    return cikti;
}

/* JSON'dan tek bir metin alanı çek. */
static char *alan(char *json, const char *ad)
{
    if (!json) return NULL;
    char *sonuc = json_metin_alani(json, ad);
    free(json);
    return sonuc;
}

char *beyin_stt(const uint8_t *wav, size_t uzunluk)
{
    /* /stt-raw: ham WAV gövdesi. Çok parçalı form kurmak ESP32'de gereksiz
     * zahmet, sunucuya bunun için ayrı bir uç eklendi. */
    return alan(gonder("/stt-raw", "audio/wav", wav, uzunluk, 4096, NULL), "text");
}

char *beyin_chat(const char *soru)
{
    char *govde = json_metin_govdesi("text", soru);
    if (!govde) return NULL;

    char *yanit = gonder("/chat", "application/json", govde, strlen(govde), 8192, NULL);
    free(govde);
    return alan(yanit, "text");
}

uint8_t *beyin_tts(const char *metin, size_t *uzunluk)
{
    char *govde = json_metin_govdesi("text", metin);
    if (!govde) { *uzunluk = 0; return NULL; }

    /* Piper WAV'ı uzun cümlelerde birkaç yüz KB olabiliyor; PSRAM'de duruyor. */
    const size_t sinir = 1024 * 1024;
    size_t gelen = 0;
    char *wav = gonder("/tts", "application/json", govde, strlen(govde), sinir, &gelen);
    free(govde);
    if (!wav || gelen < 44) { free(wav); *uzunluk = 0; return NULL; }

    /* Gerçekten gelen bayt sayısını kullanıyoruz. Başlıktaki RIFF uzunluğuna
     * güvenmek, yanıt kırpıldığında tamponun dışını okumak demek olurdu. */
    *uzunluk = gelen;
    return (uint8_t *)wav;
}
