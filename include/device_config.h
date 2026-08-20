#pragma once

#include <Arduino.h>

struct DeviceConfig {
    char mqttHost[64];
    uint16_t mqttPort;
    char mqttUser[32];
    char mqttPassword[64];
    char deviceId[32];
};

class DeviceConfigStore {
public:
    DeviceConfigStore();

    bool begin();
    const DeviceConfig &config() const;
    DeviceConfig &config();
    bool save();
    void reset();
    bool isConfigured() const;

private:
    DeviceConfig config_;
};
