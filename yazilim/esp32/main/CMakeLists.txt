idf_component_register(
    SRCS "main.c" "ses.c" "ag.c" "portal.c" "uyandirma.cc"
    INCLUDE_DIRS "."
    REQUIRES driver esp_wifi esp_http_client esp_http_server nvs_flash esp_netif json spiffs esp_psram
)
