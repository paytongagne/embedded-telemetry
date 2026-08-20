#include <Arduino.h>

#include "command.h"
#include "config.h"
#include "sensors.h"
#include "system_state.h"
#include "telemetry.h"
#include "wifi_transport.h"

SensorManager sensors;
RuntimeState runtime;
WifiTransport wifiTransport;

void setup() {
    Serial.begin(config::SERIAL_BAUD);
    Serial.setTimeout(50);
    delay(1000);

    Serial.println();
    Serial.println("========================================");
    Serial.println(" EMBEDDED TELEMETRY PLATFORM");
    Serial.print(" Firmware v");
    Serial.println(config::FIRMWARE_VERSION);
    Serial.println("========================================");

    sensors.begin();
    sensors.scanI2C();
    wifiTransport.begin();

    Serial.println();
    printStatus(sensors, runtime, Serial);
    Serial.print("WiFi transport: ");
    Serial.println(wifiTransport.enabled() ? "ENABLED" : "DISABLED");
    Serial.println("=== TELEMETRY STREAM START ===");

    runtime.lastTelemetryMs = millis();
}

void loop() {
    processSerialInput(sensors, runtime);
    wifiTransport.loop(sensors, runtime);

    const unsigned long now = millis();
    sensors.serviceHealth(now);

    if (
        !runtime.telemetryPaused &&
        now - runtime.lastTelemetryMs >= runtime.telemetryIntervalMs
    ) {
        runtime.lastTelemetryMs = now;
        const String packet = buildTelemetryPacket(sensors, runtime);
        Serial.println(packet);
        wifiTransport.publishTelemetry(packet);
    }

    yield();
}
