#pragma once

#include <Arduino.h>

#include "sensors.h"
#include "system_state.h"

class WifiTransport {
public:
    WifiTransport();

    void begin();
    void loop(SensorManager &sensors, RuntimeState &runtime);
    void publishTelemetry(const String &packet);
    void queueCommand(const String &command);
    bool enabled() const;
    bool wifiConnected() const;
    bool mqttConnected() const;
    String deviceId() const;
    String ipAddress() const;

private:
    void serviceWifi();
    void serviceMqtt();
    void subscribeTopics();
    void processPendingCommand(SensorManager &sensors, RuntimeState &runtime);
    void publishResponseLines(const String &buffer);

    unsigned long lastWifiAttemptMs_ = 0;
    unsigned long lastMqttAttemptMs_ = 0;
    String pendingCommand_;
};
