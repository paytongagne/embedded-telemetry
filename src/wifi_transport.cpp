#include "wifi_transport.h"

#include <ESP8266WiFi.h>
#include <PubSubClient.h>
#include <WiFiManager.h>

#include <cstring>

#include "command.h"
#include "wifi_config.h"

namespace {
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
WifiTransport *activeTransport = nullptr;

String makeTopic(const String &deviceId, const char *suffix) {
    return String("embedded-telemetry/") + deviceId + "/" + suffix;
}

class BufferPrint : public Print {
public:
    size_t write(uint8_t value) override {
        buffer_ += static_cast<char>(value);
        return 1;
    }

    const String &buffer() const {
        return buffer_;
    }

private:
    String buffer_;
};

void copyValue(char *destination, size_t destinationSize, const char *source) {
    if (destinationSize == 0) {
        return;
    }
    strncpy(destination, source == nullptr ? "" : source, destinationSize - 1);
    destination[destinationSize - 1] = '\0';
}
}

WifiTransport::WifiTransport() = default;

void WifiTransport::begin() {
    activeTransport = this;
    configurationLoaded_ = configStore_.begin();

    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);

    provisioningSucceeded_ = runProvisioning();
    configureMqttClient();
}

bool WifiTransport::runProvisioning() {
    DeviceConfig &config = configStore_.config();

    char portValue[6];
    snprintf(portValue, sizeof(portValue), "%u", config.mqttPort);

    WiFiManagerParameter mqttHostParam(
        "mqtt_host",
        "MQTT broker host or IP",
        config.mqttHost,
        sizeof(config.mqttHost)
    );
    WiFiManagerParameter mqttPortParam(
        "mqtt_port",
        "MQTT port",
        portValue,
        sizeof(portValue)
    );
    WiFiManagerParameter mqttUserParam(
        "mqtt_user",
        "MQTT username (optional)",
        config.mqttUser,
        sizeof(config.mqttUser)
    );
    WiFiManagerParameter mqttPasswordParam(
        "mqtt_password",
        "MQTT password (optional)",
        config.mqttPassword,
        sizeof(config.mqttPassword),
        "type='password'"
    );
    WiFiManagerParameter deviceIdParam(
        "device_id",
        "Device name",
        config.deviceId,
        sizeof(config.deviceId)
    );

    WiFiManager manager;
    manager.setConfigPortalTimeout(wifi_config::PORTAL_TIMEOUT_SECONDS);
    manager.setConnectTimeout(20);
    manager.setTitle("Embedded Telemetry Setup");
    manager.addParameter(&mqttHostParam);
    manager.addParameter(&mqttPortParam);
    manager.addParameter(&mqttUserParam);
    manager.addParameter(&mqttPasswordParam);
    manager.addParameter(&deviceIdParam);

    bool saveRequested = false;
    manager.setSaveConfigCallback([&saveRequested]() {
        saveRequested = true;
    });

    const String accessPoint = setupAccessPointName();
    const bool needsInitialSetup = !configStore_.isConfigured();

    Serial.println();
    if (needsInitialSetup) {
        Serial.println("Wireless configuration required.");
        Serial.print("Connect to setup network: ");
        Serial.println(accessPoint);
    }

    const bool connected = needsInitialSetup
        ? manager.startConfigPortal(accessPoint.c_str())
        : manager.autoConnect(accessPoint.c_str());

    if (!connected) {
        Serial.println("WiFi provisioning timed out; USB telemetry remains available.");
        return false;
    }

    if (saveRequested || needsInitialSetup) {
        copyValue(config.mqttHost, sizeof(config.mqttHost), mqttHostParam.getValue());
        config.mqttPort = static_cast<uint16_t>(atoi(mqttPortParam.getValue()));
        if (config.mqttPort == 0) {
            config.mqttPort = 1883;
        }
        copyValue(config.mqttUser, sizeof(config.mqttUser), mqttUserParam.getValue());
        copyValue(config.mqttPassword, sizeof(config.mqttPassword), mqttPasswordParam.getValue());
        copyValue(config.deviceId, sizeof(config.deviceId), deviceIdParam.getValue());
        if (config.deviceId[0] == '\0') {
            copyValue(config.deviceId, sizeof(config.deviceId), "esp8285-node");
        }

        if (!configStore_.save()) {
            Serial.println("Warning: unable to persist network configuration.");
        }
    }

    Serial.print("WiFi connected: ");
    Serial.println(WiFi.SSID());
    Serial.print("IP address: ");
    Serial.println(WiFi.localIP());
    return configStore_.isConfigured();
}

void WifiTransport::configureMqttClient() {
    const DeviceConfig &config = configStore_.config();

    if (!configStore_.isConfigured()) {
        return;
    }

    mqttClient.setServer(config.mqttHost, config.mqttPort);
    mqttClient.setBufferSize(wifi_config::MQTT_BUFFER_SIZE);
    mqttClient.setKeepAlive(wifi_config::MQTT_KEEPALIVE_SECONDS);

    mqttClient.setCallback([](char *topic, byte *payload, unsigned int length) {
        if (activeTransport == nullptr) {
            return;
        }

        const String expectedTopic = makeTopic(activeTransport->deviceId(), "command");
        if (String(topic) != expectedTopic) {
            return;
        }

        String command;
        command.reserve(length);
        for (unsigned int i = 0; i < length; ++i) {
            command += static_cast<char>(payload[i]);
        }
        activeTransport->queueCommand(command);
    });
}

void WifiTransport::queueCommand(const String &command) {
    pendingCommand_ = command;
}

void WifiTransport::serviceWifi() {
    if (!configured() || WiFi.status() == WL_CONNECTED) {
        return;
    }

    const unsigned long now = millis();
    if (now - lastWifiAttemptMs_ < wifi_config::RECONNECT_INTERVAL_MS) {
        return;
    }

    lastWifiAttemptMs_ = now;
    WiFi.reconnect();
}

void WifiTransport::serviceMqtt() {
    if (!configured() || WiFi.status() != WL_CONNECTED) {
        return;
    }

    if (mqttClient.connected()) {
        mqttClient.loop();
        return;
    }

    const unsigned long now = millis();
    if (now - lastMqttAttemptMs_ < wifi_config::RECONNECT_INTERVAL_MS) {
        return;
    }
    lastMqttAttemptMs_ = now;

    const DeviceConfig &config = configStore_.config();
    const String clientId = String("embedded-telemetry-") + config.deviceId;
    const String availability = makeTopic(config.deviceId, "availability");

    bool connected = false;
    if (strlen(config.mqttUser) > 0) {
        connected = mqttClient.connect(
            clientId.c_str(),
            config.mqttUser,
            config.mqttPassword,
            availability.c_str(),
            1,
            true,
            "offline"
        );
    } else {
        connected = mqttClient.connect(
            clientId.c_str(),
            availability.c_str(),
            1,
            true,
            "offline"
        );
    }

    if (connected) {
        mqttClient.publish(availability.c_str(), "online", true);
        subscribeTopics();
        Serial.print("MQTT connected: ");
        Serial.print(config.mqttHost);
        Serial.print(":");
        Serial.println(config.mqttPort);
    }
}

void WifiTransport::subscribeTopics() {
    if (!mqttClient.connected()) {
        return;
    }

    mqttClient.subscribe(makeTopic(deviceId(), "command").c_str(), 1);
}

void WifiTransport::processPendingCommand(SensorManager &sensors, RuntimeState &runtime) {
    if (pendingCommand_.length() == 0) {
        return;
    }

    String command = pendingCommand_;
    pendingCommand_ = "";

    BufferPrint output;
    processCommand(command, sensors, runtime, output);
    publishResponseLines(output.buffer());
}

void WifiTransport::publishResponseLines(const String &buffer) {
    if (!mqttClient.connected() || buffer.length() == 0) {
        return;
    }

    const String topic = makeTopic(deviceId(), "response");
    int start = 0;
    while (start < static_cast<int>(buffer.length())) {
        int end = buffer.indexOf('\n', start);
        if (end < 0) {
            end = buffer.length();
        }

        String line = buffer.substring(start, end);
        line.trim();
        if (line.length() > 0) {
            mqttClient.publish(topic.c_str(), line.c_str(), false);
        }
        start = end + 1;
    }
}

void WifiTransport::loop(SensorManager &sensors, RuntimeState &runtime) {
    serviceWifi();
    serviceMqtt();
    processPendingCommand(sensors, runtime);
}

void WifiTransport::publishTelemetry(const String &packet) {
    if (mqttClient.connected()) {
        mqttClient.publish(makeTopic(deviceId(), "telemetry").c_str(), packet.c_str(), false);
    }
}

bool WifiTransport::enabled() const {
    return true;
}

bool WifiTransport::wifiConnected() const {
    return WiFi.status() == WL_CONNECTED;
}

bool WifiTransport::mqttConnected() const {
    return mqttClient.connected();
}

bool WifiTransport::configured() const {
    return configStore_.isConfigured();
}

String WifiTransport::deviceId() const {
    return configStore_.config().deviceId;
}

String WifiTransport::ipAddress() const {
    return WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : String("");
}

String WifiTransport::mqttHost() const {
    return configStore_.config().mqttHost;
}

String WifiTransport::setupAccessPointName() const {
    String name = wifi_config::SETUP_AP_PREFIX;
    name += "-";
    name += String(ESP.getChipId(), HEX);
    name.toUpperCase();
    return name;
}
