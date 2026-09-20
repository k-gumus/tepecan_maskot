idf_component_register(
    SRCS "main.c" "ses.c" "ag.c" "portal.c" "uyandirma.cc"
    INCLUDE_DIRS "."
    REQUIRES esp_driver_i2s esp_driver_gpio driver esp_wifi esp_http_client
             esp_http_server nvs_flash esp_netif esp_psram
)
