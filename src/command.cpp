#include "command.h"

#include "config.h"
#include "system_state.h"

static void acknowledge(Print &output, const String &command) {
    output.print("ACK,");
    output.println(command);
}

static void sendError(
    Print &output,
    const String &error,
    const String &details = ""
) {
    output.print("ERR,");
    output.print(error);

    if (details.length() > 0) {
        output.print(",");
        output.print(details);
    }

    output.println();
}

void printStatus(
    const SensorManager &sensors,
    const RuntimeState &runtime,
    Print &output
) {
    const SystemState state = determineSystemState(
        sensors.bmeHealthy(),
        sensors.imuHealthy()
    );
    const HealthCounters &counters = sensors.counters();

    output.print("STATUS,STATE=");
    output.print(stateToString(state));
    output.print(",BME=");
    output.print(sensors.bmeHealthy() ? "OK" : "FAULT");
    output.print(",IMU=");
    output.print(sensors.imuHealthy() ? "OK" : "FAULT");
    output.print(",AUX=");
    output.print(sensors.auxPresent() ? "PRESENT" : "ABSENT");
    output.print(",PAUSED=");
    output.print(runtime.telemetryPaused ? "1" : "0");
    output.print(",RATE_MS=");
    output.print(runtime.telemetryIntervalMs);
    output.print(",I2C_ERR=");
    output.print(counters.i2cErrors);
    output.print(",RECOVERY=");
    output.print(counters.successfulRecoveries);
    output.print(",RECOVERY_ATTEMPTS=");
    output.print(counters.recoveryAttempts);
    output.print(",BME_FAIL=");
    output.print(counters.bmeFailures);
    output.print(",IMU_FAIL=");
    output.print(counters.imuFailures);
    output.print(",FW=");
    output.println(config::FIRMWARE_VERSION);
}

void processCommand(
    String line,
    SensorManager &sensors,
    RuntimeState &runtime,
    Print &output
) {
    line.trim();
    if (line.length() == 0) {
        return;
    }

    if (!line.startsWith("CMD,")) {
        sendError(output, "BAD_FORMAT", line);
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
        acknowledge(output, "STATUS");
        printStatus(sensors, runtime, output);
        return;
    }

    if (command == "PAUSE") {
        runtime.telemetryPaused = true;
        acknowledge(output, "PAUSE");
        printStatus(sensors, runtime, output);
        return;
    }

    if (command == "RESUME") {
        runtime.telemetryPaused = false;
        runtime.lastTelemetryMs = millis();
        acknowledge(output, "RESUME");
        printStatus(sensors, runtime, output);
        return;
    }

    if (command == "SET_RATE") {
        if (value.length() == 0) {
            sendError(output, "MISSING_VALUE", "SET_RATE");
            return;
        }

        const long requestedRate = value.toInt();
        if (
            requestedRate < static_cast<long>(config::MIN_TELEMETRY_INTERVAL_MS) ||
            requestedRate > static_cast<long>(config::MAX_TELEMETRY_INTERVAL_MS)
        ) {
            sendError(output, "RATE_RANGE", "100-10000");
            return;
        }

        runtime.telemetryIntervalMs = static_cast<unsigned long>(requestedRate);
        output.print("ACK,SET_RATE,");
        output.println(runtime.telemetryIntervalMs);
        printStatus(sensors, runtime, output);
        return;
    }

    if (command == "INJECT_FAULT") {
        if (value != "IMU" && value != "BME") {
            sendError(output, "BAD_TARGET", value);
            return;
        }

        sensors.injectFault(value);
        output.print("ACK,INJECT_FAULT,");
        output.println(value);
        printStatus(sensors, runtime, output);
        return;
    }

    if (command == "CLEAR_FAULTS") {
        sensors.clearInjectedFaults();
        acknowledge(output, "CLEAR_FAULTS");
        printStatus(sensors, runtime, output);
        return;
    }

    if (command == "RESET") {
        acknowledge(output, "RESET");
        Serial.flush();
        delay(150);
        ESP.restart();
        return;
    }

    sendError(output, "UNKNOWN_COMMAND", command);
}

void processSerialInput(SensorManager &sensors, RuntimeState &runtime) {
    while (Serial.available() > 0) {
        String line = Serial.readStringUntil('\n');
        processCommand(line, sensors, runtime, Serial);
    }
}
