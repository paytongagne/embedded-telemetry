#include "telemetry.h"

#include "system_state.h"

uint16_t crc16Ccitt(const String &payload) {
    uint16_t crc = 0xFFFF;

    for (size_t i = 0; i < payload.length(); i++) {
        crc ^= static_cast<uint16_t>(payload[i]) << 8;

        for (uint8_t bit = 0; bit < 8; bit++) {
            if (crc & 0x8000) {
                crc = (crc << 1) ^ 0x1021;
            } else {
                crc <<= 1;
            }
        }
    }

    return crc;
}

static String crcHex(uint16_t crc) {
    String value(crc, HEX);
    value.toUpperCase();

    while (value.length() < 4) {
        value = String("0") + value;
    }

    return value;
}

static void appendField(String &packet, const char *name, const String &value) {
    packet += ",";
    packet += name;
    packet += "=";
    packet += value;
}

String buildTelemetryPacket(SensorManager &sensors, RuntimeState &runtime) {
    runtime.sequenceNumber++;

    const EnvironmentSample environment = sensors.readEnvironment();
    const MotionSample motion = sensors.readMotion();
    const HealthCounters &counters = sensors.counters();

    String packet = "TEL,";
    packet += String(runtime.sequenceNumber);
    appendField(packet, "TIME", String(millis()));

    if (environment.valid) {
        appendField(packet, "TEMP", String(environment.temperature, 2));
        appendField(packet, "PRESS", String(environment.pressure, 2));
        appendField(packet, "HUM", String(environment.humidity, 2));
    }

    if (motion.valid) {
        appendField(packet, "AX", String(motion.ax, 3));
        appendField(packet, "AY", String(motion.ay, 3));
        appendField(packet, "AZ", String(motion.az, 3));
        appendField(packet, "GX", String(motion.gx, 2));
        appendField(packet, "GY", String(motion.gy, 2));
        appendField(packet, "GZ", String(motion.gz, 2));
    }

    appendField(packet, "BME", sensors.bmeHealthy() ? "OK" : "FAULT");
    appendField(packet, "IMU", sensors.imuHealthy() ? "OK" : "FAULT");
    appendField(packet, "AUX", sensors.auxPresent() ? "PRESENT" : "ABSENT");
    appendField(packet, "I2C_ERR", String(counters.i2cErrors));
    appendField(packet, "RECOVERY", String(counters.successfulRecoveries));
    appendField(packet, "RECOVERY_ATTEMPTS", String(counters.recoveryAttempts));
    appendField(packet, "BME_FAIL", String(counters.bmeFailures));
    appendField(packet, "IMU_FAIL", String(counters.imuFailures));

    const SystemState state = determineSystemState(
        sensors.bmeHealthy(),
        sensors.imuHealthy()
    );

    appendField(packet, "STATUS", stateToString(state));

    const uint16_t crc = crc16Ccitt(packet);
    appendField(packet, "CRC", crcHex(crc));
    return packet;
}

void emitTelemetry(SensorManager &sensors, RuntimeState &runtime) {
    Serial.println(buildTelemetryPacket(sensors, runtime));
}
