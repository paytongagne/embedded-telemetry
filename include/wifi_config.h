#pragma once

#include <Arduino.h>

#if __has_include("wifi_secrets.h")
#include "wifi_secrets.h"
#define WIFI_TELEMETRY_ENABLED 1
#else
#define WIFI_TELEMETRY_ENABLED 0
namespace wifi_secrets {
constexpr const char *SSID = "";
constexpr const char *PASSWORD = "";
constexpr const char *MQTT_HOST = "";
constexpr uint16_t MQTT_PORT = 1883;
constexpr const char *MQTT_USER = "";
constexpr const char *MQTT_PASSWORD = "";
constexpr const char *DEVICE_ID = "esp8285-node";
}
#endif

namespace wifi_config {
constexpr uint32_t RECONNECT_INTERVAL_MS = 5000;
constexpr uint16_t MQTT_BUFFER_SIZE = 768;
constexpr uint16_t MQTT_KEEPALIVE_SECONDS = 20;
}
