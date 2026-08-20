#pragma once

#include <Arduino.h>

namespace config {
constexpr uint32_t SERIAL_BAUD = 115200;
constexpr uint8_t BME_ADDRESS = 0x76;
constexpr uint8_t MPU_ADDRESS = 0x68;
constexpr uint8_t AUX_ADDRESS = 0x29;
constexpr uint32_t DEFAULT_TELEMETRY_INTERVAL_MS = 1000;
constexpr uint32_t MIN_TELEMETRY_INTERVAL_MS = 100;
constexpr uint32_t MAX_TELEMETRY_INTERVAL_MS = 10000;
constexpr uint32_t HEALTH_CHECK_INTERVAL_MS = 5000;
constexpr const char *FIRMWARE_VERSION = "1.1.0";
}
