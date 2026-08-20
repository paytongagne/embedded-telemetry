#include "wifi_transport.h"

#include <ESP8266WiFi.h>
#include <PubSubClient.h>

#include "command.h"
#include "wifi_config.h"

namespace {
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
WifiTransport *activeTransport = nullptr;

String telemetryTopic() {
    return String("embedded-telemetry/") + wifi_secrets::DEVICE_ID + "/telemetry";
}

String commandTopic() {
    return String("embedded-telemetry/") + wifi_secrets::DEVICE_ID + "/command";
}

String responseTopic() {
    return String("embedded-telemetry/") + wifi_secrets::DEVICE_ID + "/response";
}

String availabilityTopic() {
    return String("embedded-telemetry/") + wifi_secrets::DEVICE_ID + "/availability";
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

void mqttCallback(char *topic, byte *payload, unsigned int length) {
    if (activeTransport == nullptr) {
        return;
    }

    String message;
    message.reserve(length);
    for (unsigned int i = 0; i < length; ++i) {
        message += static_cast<char>(payload[i]);
    }

    if (String(topic) == commandTopic()) {
        activeTransport->loop;
    }
}
}

WifiTransport::WifiTransport() = default;

void WifiTransport::begin() {
#if WIFI_TELEMETRY_ENABLED
    activeTransport = this;
    WiFi.mode(WIFI_STA);
    WiFi.persistent(false);
    WiFi.setAutoReconnect(true);

    mqttClient.setServer(wifi_secrets::MQTT_HOST, wifi_secrets::MQTT_PORT);
    mqttClient.setBufferSize(wifi_config::MQTT_BUFFER_SIZE);
    mqttClient.setKeepAlive(wifi_config::MQTT_KEEPALIVE_SECONDS);

    mqttClient.setCallback([](char *topic, byte *payload, unsigned int length) {
        if (activeTransport == nullptr) {
            return;
        }

        if (String(topic) != commandTopic()) {
            return;
        }

        String command;
        command.reserve(length);
        for (unsigned int i = 0; i < length; ++i) {
            command += static_cast<char>(payload[i]);
        }
        activeTransport->pendingCommand_ = command;
    });

    serviceWifi();
#endif
}

void WifiTransport::serviceWifi() {
#if WIFI_TELEMETRY_ENABLED
    if (WiFi.status() == WL_CONNECTED) {
        return;
    }

    const unsigned long now = millis();
    if (now - lastWifiAttemptMs_ < wifi_config::RECONNECT_INTERVAL_MS) {
        return;
    }

    lastWifiAttemptMs_ = now;
    WiFi.begin(wifi_secrets::SSID, wifi_secrets::PASSWORD);
#endif
}

void WifiTransport::serviceMqtt() {
#if WIFI_TELEMETRY_ENABLED
    if (WiFi.status() != WL_CONNECTED) {
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

    const String clientId = String("embedded-telemetry-") + wifi_secrets::DEVICE_ID;
    const String availability = availabilityTopic();

    bool connected = false;
    if (strlen(wifi_secrets::MQTT_USER) > 0) {
        connected = mqttClient.connect(
            clientId.c_str(),
            wifi_secrets::MQTT_USER,
            wifi_secrets::MQTT_PASSWORD,
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
    }
#endif
}

void WifiTransport::subscribeTopics() {
#if WIFI_TELEMETRY_ENABLED
    mqttClient.subscribe(commandTopic().c_str(), 1);
#endif
}

void WifiTransport::processPendingCommand(SensorManager &sensors, RuntimeState &runtime) {
#if WIFI_TELEMETRY_ENABLED
    if (pendingCommand_.length() == 0) {
        return;
    }

    String command = pendingCommand_;
    pendingCommand_ = "";

    BufferPrint output;
    processCommand(command, sensors, runtime, output);
    publishResponseLines(output.buffer());
#endif
}

void WifiTransport::publishResponseLines(const String &buffer) {
#if WIFI_TELEMETRY_ENABLED
    if (!mqttClient.connected() || buffer.length() == 0) {
        return;
    }

    int start = 0;
    while (start < static_cast<int>(buffer.length())) {
        int end = buffer.indexOf('\n', start);
        if (end < 0) {
            end = buffer.length();
        }

        String line = buffer.substring(start, end);
        line.trim();
        if (line.length() > 0) {
            mqttClient.publish(responseTopic().c_str(), line.c_str(), false);
        }
        start = end + 1;
    }
#endif
}

void WifiTransport::loop(SensorManager &sensors, RuntimeState &runtime) {
#if WIFI_TELEMETRY_ENABLED
    serviceWifi();
    serviceMqtt();
    processPendingCommand(sensors, runtime);
#else
    (void)sensors;
    (void)runtime;
#endif
}

void WifiTransport::publishTelemetry(const String &packet) {
#if WIFI_TELEMETRY_ENABLED
    if (mqttClient.connected()) {
        mqttClient.publish(telemetryTopic().c_str(), packet.c_str(), false);
    }
#else
    (void)packet;
#endif
}

bool WifiTransport::enabled() const {
    return WIFI_TELEMETRY_ENABLED;
}

bool WifiTransport::wifiConnected() const {
#if WIFI_TELEMETRY_ENABLED
    return WiFi.status() == WL_CONNECTED;
#else
    return false;
#endif
}

bool WifiTransport::mqttConnected() const {
#if WIFI_TELEMETRY_ENABLED
    return mqttClient.connected();
#else
    return false;
#endif
}

String WifiTransport::deviceId() const {
    return wifi_secrets::DEVICE_ID;
}

String WifiTransport::ipAddress() const {
#if WIFI_TELEMETRY_ENABLED
    return WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : String("");
#else
    return String("");
#endif
}
