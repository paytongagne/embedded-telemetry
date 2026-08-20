#pragma once

#include <Arduino.h>
#include "config.h"

enum class SystemState {
    NORMAL,
    DEGRADED,
    FAULT,
};

struct RuntimeState {
    unsigned long sequenceNumber = 0;
    unsigned long telemetryIntervalMs = config::DEFAULT_TELEMETRY_INTERVAL_MS;
    unsigned long lastTelemetryMs = 0;
    bool telemetryPaused = false;
};

SystemState determineSystemState(bool bmeHealthy, bool imuHealthy);
const char *stateToString(SystemState state);
