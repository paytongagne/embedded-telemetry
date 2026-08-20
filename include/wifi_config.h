#pragma once

#include <Arduino.h>

namespace wifi_config {
constexpr uint32_t RECONNECT_INTERVAL_MS = 5000;
constexpr uint32_t PORTAL_TIMEOUT_SECONDS = 180;
constexpr uint16_t MQTT_BUFFER_SIZE = 768;
constexpr uint16_t MQTT_KEEPALIVE_SECONDS = 20;
constexpr uint16_t DIRECT_TCP_PORT = 9000;
constexpr const char *SETUP_AP_PREFIX = "EmbeddedTelemetry-Setup";
}
