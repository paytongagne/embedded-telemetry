#pragma once

#include <Arduino.h>

#include "sensors.h"
#include "system_state.h"

void printStatus(
    const SensorManager &sensors,
    const RuntimeState &runtime,
    Print &output
);

void processCommand(
    String line,
    SensorManager &sensors,
    RuntimeState &runtime,
    Print &output
);

void processSerialInput(SensorManager &sensors, RuntimeState &runtime);
