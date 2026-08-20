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
    String value = String(crc, HEX);
    value.toUpperCase();
    while (value.length() < 4) {
        value = "0" + value;
    }
    return value;
}

String buildTelemetryPacket(SensorManager &sensors, RuntimeState &runtime) {
    runtime.sequenceNumber++;

    const EnvironmentSample environment = sensors.readEnvironment();
    const MotionSample motion = sensors.readMotion();
    const HealthCounters &counters = sensors.counters();

    String packet = "TEL,";
    packet += String(runtime.sequenceNumber);
    packet += ",TIME=" + String(millis());

    if (environment.valid) {
        packet += ",TEMP=" + String(environment.temperature, 2);
        packet += ",PRESS=" + String(environment.pressure, 2);
        packet += ",HUM=" + String(environment.humidity, 2);
    }

    if (motion.valid) {
        packet += ",AX=" + String(motion.ax, 3);
        packet += ",AY=" + String(motion.ay, 3);
        packet += ",AZ=" + String(motion.az, 3);
        packet += ",GX=" + String(motion.gx, 2);
        packet += ",GY=" + String(motion.gy, 2);
        packet += ",GZ=" + String(motion.gz, 2);
    }

    packet += ",BME=";
    packet += sensors.bmeHealthy() ? "OK" : "FAULT";
    packet += ",IMU=";
    packet += sensors.imuHealthy() ? "OK" : "FAULT";
    packet += ",AUX=";
    packet += sensors.auxPresent() ? "PRESENT" : "ABSENT";
    packet += ",I2C_ERR=" + String(counters.i2cErrors);
    packet += ",RECOVERY=" + String(counters.successfulRecoveries);
    packet += ",BME_FAIL=" + String(counters.bmeFailures);
    packet += ",IMU_FAIL=" + String(counters.imuFailures);

    const SystemState state = determineSystemState(
        sensors.bmeHealthy(),
        sensors.imuHealthy()
    );

    packet += ",STATUS=";
    packet += stateToString(state);

    const uint16_t crc = crc16Ccitt(packet);
    packet += ",CRC=" + crcHex(crc);
    return packet;
}

void emitTelemetry(SensorManager &sensors, RuntimeState &runtime) {
    Serial.println(buildTelemetryPacket(sensors, runtime));
}
