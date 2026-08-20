#include "command.h"

#include "config.h"
#include "system_state.h"

static void acknowledge(const String &command) {
    Serial.print("ACK,");
    Serial.println(command);
}

static void sendError(const String &error, const String &details = "") {
    Serial.print("ERR,");
    Serial.print(error);

    if (details.length() > 0) {
        Serial.print(",");
        Serial.print(details);
    }

    Serial.println();
}

void printStatus(const SensorManager &sensors, const RuntimeState &runtime) {
    const SystemState state = determineSystemState(
        sensors.bmeHealthy(),
        sensors.imuHealthy()
    );
    const HealthCounters &counters = sensors.counters();

    Serial.print("STATUS,STATE=");
    Serial.print(stateToString(state));
    Serial.print(",BME=");
    Serial.print(sensors.bmeHealthy() ? "OK" : "FAULT");
    Serial.print(",IMU=");
    Serial.print(sensors.imuHealthy() ? "OK" : "FAULT");
    Serial.print(",AUX=");
    Serial.print(sensors.auxPresent() ? "PRESENT" : "ABSENT");
    Serial.print(",PAUSED=");
    Serial.print(runtime.telemetryPaused ? "1" : "0");
    Serial.print(",RATE_MS=");
    Serial.print(runtime.telemetryIntervalMs);
    Serial.print(",I2C_ERR=");
    Serial.print(counters.i2cErrors);
    Serial.print(",RECOVERY=");
    Serial.print(counters.successfulRecoveries);
    Serial.print(",RECOVERY_ATTEMPTS=");
    Serial.print(counters.recoveryAttempts);
    Serial.print(",BME_FAIL=");
    Serial.print(counters.bmeFailures);
    Serial.print(",IMU_FAIL=");
    Serial.print(counters.imuFailures);
    Serial.print(",FW=");
    Serial.println(config::FIRMWARE_VERSION);
}

void processCommand(String line, SensorManager &sensors, RuntimeState &runtime) {
    line.trim();
    if (line.length() == 0) {
        return;
    }

    if (!line.startsWith("CMD,")) {
        sendError("BAD_FORMAT", line);
        return;
    }

    line.remove(0, 4);
    const int separator = line.indexOf(',');
    String command = separator >= 0 ? line.substring(0, separator) : line;
    String value = separator >= 0 ? line.substring(separator + 1) : "";

    command.trim();
    value.trim();
    command.toUpperCase();
    value.toUpperCase();

    if (command == "STATUS") {
        acknowledge("STATUS");
        printStatus(sensors, runtime);
        return;
    }

    if (command == "PAUSE") {
        runtime.telemetryPaused = true;
        acknowledge("PAUSE");
        printStatus(sensors, runtime);
        return;
    }

    if (command == "RESUME") {
        runtime.telemetryPaused = false;
        runtime.lastTelemetryMs = millis();
        acknowledge("RESUME");
        printStatus(sensors, runtime);
        return;
    }

    if (command == "SET_RATE") {
        if (value.length() == 0) {
            sendError("MISSING_VALUE", "SET_RATE");
            return;
        }

        const long requestedRate = value.toInt();
        if (
            requestedRate < static_cast<long>(config::MIN_TELEMETRY_INTERVAL_MS) ||
            requestedRate > static_cast<long>(config::MAX_TELEMETRY_INTERVAL_MS)
        ) {
            sendError("RATE_RANGE", "100-10000");
            return;
        }

        runtime.telemetryIntervalMs = static_cast<unsigned long>(requestedRate);
        Serial.print("ACK,SET_RATE,");
        Serial.println(runtime.telemetryIntervalMs);
        printStatus(sensors, runtime);
        return;
    }

    if (command == "INJECT_FAULT") {
        if (value != "IMU" && value != "BME") {
            sendError("BAD_TARGET", value);
            return;
        }

        sensors.injectFault(value);
        Serial.print("ACK,INJECT_FAULT,");
        Serial.println(value);
        printStatus(sensors, runtime);
        return;
    }

    if (command == "CLEAR_FAULTS") {
        sensors.clearInjectedFaults();
        acknowledge("CLEAR_FAULTS");
        printStatus(sensors, runtime);
        return;
    }

    if (command == "RESET") {
        acknowledge("RESET");
        Serial.flush();
        delay(100);
        ESP.restart();
        return;
    }

    sendError("UNKNOWN_COMMAND", command);
}

void processSerialInput(SensorManager &sensors, RuntimeState &runtime) {
    while (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        processCommand(line, sensors, runtime);
    }
}
