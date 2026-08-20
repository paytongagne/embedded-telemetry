#pragma once

#include <Arduino.h>

#include "sensors.h"
#include "system_state.h"

uint16_t crc16Ccitt(const String &payload);
String buildTelemetryPacket(SensorManager &sensors, RuntimeState &runtime);
void emitTelemetry(SensorManager &sensors, RuntimeState &runtime);
