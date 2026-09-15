/* İlk kurulum: kart kendi erişim noktasını açıyor, telefondan ağ ve beyin
 * adresi giriliyor, NVS'e yazılıp yeniden başlıyor.
 *
 * Böylece SSID'yi koda gömmek gerekmiyor: maskot kulüpten etkinliğe
 * giderken ağ değiştirmek için bilgisayara bağlanmaya gerek kalmıyor.
 */
#include <string.h>
#include <stdlib.h>
#include "esp_log.h"
#include "esp_wifi.h"
#include "esp_netif.h"
#include "esp_event.h"
#include "esp_http_server.h"
#include "esp_system.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "ag.h"

static const char *ETIKET = "portal";

#define AP_SSID "Tepecan-Kurulum"

static const char SAYFA[] =
    "<!doctype html><meta charset=utf-8>"
    "<meta name=viewport content='width=device-width,initial-scale=1'>"
    "<title>Tepecan kurulum</title>"
    "<style>body{font-family:system-ui;margin:0;padding:24px;background:#12161c;"
    "color:#e8eef6}h1{font-size:20px;color:#5aa9f8}label{display:block;margin:14px 0 4px}"
    "input{width:100%;box-sizing:border-box;padding:10px;border-radius:8px;"
    "border:1px solid #33404f;background:#1b222c;color:#e8eef6;font-size:16px}"
    "button{margin-top:20px;width:100%;padding:12px;border:0;border-radius:8px;"
    "background:#1f5fa9;color:#fff;font-size:16px}</style>"
    "<h1>Tepecan kurulum</h1>"
    "<form method=post action=/kaydet>"
    "<label>Wi-Fi adi</label><input name=ssid required>"
    "<label>Wi-Fi sifresi</label><input name=sifre type=password>"
    "<label>Beyin sunucusu</label>"
    "<input name=beyin value='http://tepecan-beyin.local:8000'>"
    "<button>Kaydet ve yeniden baslat</button></form>";

static esp_err_t sayfa_ver(httpd_req_t *r)
{
    httpd_resp_set_type(r, "text/html; charset=utf-8");
    return httpd_resp_send(r, SAYFA, HTTPD_RESP_USE_STRLEN);
}

/* application/x-www-form-urlencoded çözücü: yalnız bize lazım olan kadarı. */
static void alan_cek(const char *govde, const char *ad, char *hedef, size_t boy)
{
    hedef[0] = '\0';
    char desen[24];
    snprintf(desen, sizeof(desen), "%s=", ad);
    const char *p = strstr(govde, desen);
    if (!p) return;
    p += strlen(desen);

    size_t i = 0;
    while (*p && *p != '&' && i + 1 < boy) {
        if (*p == '+') { hedef[i++] = ' '; p++; }
        else if (*p == '%' && p[1] && p[2]) {
            char h[3] = { p[1], p[2], 0 };
            hedef[i++] = (char)strtol(h, NULL, 16);
            p += 3;
        } else hedef[i++] = *p++;
    }
    hedef[i] = '\0';
}

static esp_err_t kaydet(httpd_req_t *r)
{
    char govde[512] = { 0 };
    int n = httpd_req_recv(r, govde, sizeof(govde) - 1);
    if (n <= 0) return ESP_FAIL;
    govde[n] = '\0';

    char ssid[64], sifre[96], beyin[160];
    alan_cek(govde, "ssid", ssid, sizeof(ssid));
    alan_cek(govde, "sifre", sifre, sizeof(sifre));
    alan_cek(govde, "beyin", beyin, sizeof(beyin));

    if (ssid[0] == '\0') {
        httpd_resp_send(r, "Wi-Fi adi bos olamaz.", HTTPD_RESP_USE_STRLEN);
        return ESP_OK;
    }
    nvs_yaz("ssid", ssid);
    nvs_yaz("sifre", sifre);
    if (beyin[0]) nvs_yaz("beyin", beyin);

    httpd_resp_set_type(r, "text/html; charset=utf-8");
    httpd_resp_send(r, "<meta charset=utf-8><h2>Kaydedildi. Yeniden baslatiliyor…</h2>",
                    HTTPD_RESP_USE_STRLEN);
    ESP_LOGI(ETIKET, "'%s' kaydedildi, yeniden başlatılıyor", ssid);
    vTaskDelay(pdMS_TO_TICKS(800));
    esp_restart();
    return ESP_OK;
}

esp_err_t kurulum_noktasi_ac(void)
{
    ESP_ERROR_CHECK(esp_netif_init());
    ESP_ERROR_CHECK(esp_event_loop_create_default());
    esp_netif_create_default_wifi_ap();

    wifi_init_config_t ayar = WIFI_INIT_CONFIG_DEFAULT();
    ESP_ERROR_CHECK(esp_wifi_init(&ayar));

    wifi_config_t wc = { 0 };
    strncpy((char *)wc.ap.ssid, AP_SSID, sizeof(wc.ap.ssid));
    wc.ap.ssid_len = strlen(AP_SSID);
    wc.ap.max_connection = 3;
    wc.ap.authmode = WIFI_AUTH_OPEN;       /* şifresiz: kurulumu kolaylaştırıyor */
    ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_AP));
    ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_AP, &wc));
    ESP_ERROR_CHECK(esp_wifi_start());

    httpd_handle_t sunucu = NULL;
    httpd_config_t hc = HTTPD_DEFAULT_CONFIG();
    ESP_ERROR_CHECK(httpd_start(&sunucu, &hc));

    httpd_uri_t kok = { .uri = "/", .method = HTTP_GET, .handler = sayfa_ver };
    httpd_uri_t post = { .uri = "/kaydet", .method = HTTP_POST, .handler = kaydet };
    httpd_register_uri_handler(sunucu, &kok);
    httpd_register_uri_handler(sunucu, &post);

    ESP_LOGW(ETIKET, "'%s' ağına bağlanıp http://192.168.4.1 adresini aç", AP_SSID);
    return ESP_ERR_NOT_FINISHED;           /* main bunu görünce beklemeye geçiyor */
}
