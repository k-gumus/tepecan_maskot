idf_component_register(
    SRCS "main.c" "ses.c" "ag.c" "portal.c" "uyandirma.cc"
    INCLUDE_DIRS "."
    # I2S ve GPIO'yu ADLARIYLA istiyoruz. ESP-IDF v6'da "driver" meta-bileşeni
    # artık bunları dışa vermiyor (REQUIRES'ı yalnız esp_hal_i2c/twai/touch_sens),
    # o yüzden sadece "driver" yazmak v6'da driver/i2s_std.h ve driver/gpio.h
    # bulunamıyor hatası veriyor. Bu iki bileşen v5.3'te de var, yani açıkça
    # yazmak iki sürümde de çalışıyor.
    REQUIRES esp_driver_i2s esp_driver_gpio driver esp_wifi esp_http_client
             esp_http_server nvs_flash esp_netif json spiffs esp_psram
)
