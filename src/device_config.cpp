#include "device_config.h"

#include <EEPROM.h>
#include <cstring>

namespace {
constexpr size_t EEPROM_SIZE = 512;
constexpr uint32_t CONFIG_MAGIC = 0x45544D31;
constexpr uint16_t CONFIG_VERSION = 1;

struct StoredConfig {
    uint32_t magic;
    uint16_t version;
    DeviceConfig config;
};

void setDefaults(DeviceConfig &config) {
    memset(&config, 0, sizeof(config));
    config.mqttPort = 1883;
    strncpy(config.deviceId, "esp8285-node", sizeof(config.deviceId) - 1);
}
}

DeviceConfigStore::DeviceConfigStore() {
    setDefaults(config_);
}

bool DeviceConfigStore::begin() {
    EEPROM.begin(EEPROM_SIZE);

    StoredConfig stored{};
    EEPROM.get(0, stored);

    if (stored.magic != CONFIG_MAGIC || stored.version != CONFIG_VERSION) {
        setDefaults(config_);
        return false;
    }

    config_ = stored.config;
    config_.mqttHost[sizeof(config_.mqttHost) - 1] = '\0';
    config_.mqttUser[sizeof(config_.mqttUser) - 1] = '\0';
    config_.mqttPassword[sizeof(config_.mqttPassword) - 1] = '\0';
    config_.deviceId[sizeof(config_.deviceId) - 1] = '\0';

    if (config_.mqttPort == 0) {
        config_.mqttPort = 1883;
    }
    if (config_.deviceId[0] == '\0') {
        strncpy(config_.deviceId, "esp8285-node", sizeof(config_.deviceId) - 1);
    }

    return true;
}

const DeviceConfig &DeviceConfigStore::config() const {
    return config_;
}

DeviceConfig &DeviceConfigStore::config() {
    return config_;
}

bool DeviceConfigStore::save() {
    StoredConfig stored{};
    stored.magic = CONFIG_MAGIC;
    stored.version = CONFIG_VERSION;
    stored.config = config_;

    EEPROM.put(0, stored);
    return EEPROM.commit();
}

void DeviceConfigStore::reset() {
    setDefaults(config_);

    StoredConfig blank{};
    EEPROM.put(0, blank);
    EEPROM.commit();
}

bool DeviceConfigStore::isConfigured() const {
    return config_.deviceId[0] != '\0';
}
