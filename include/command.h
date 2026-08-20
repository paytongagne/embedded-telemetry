#pragma once

#include <Arduino.h>

#include "sensors.h"
#include "system_state.h"

void printStatus(const SensorManager &sensors, const RuntimeState &runtime);
void processCommand(String line, SensorManager &sensors, RuntimeState &runtime);
void processSerialInput(SensorManager &sensors, RuntimeState &runtime);
