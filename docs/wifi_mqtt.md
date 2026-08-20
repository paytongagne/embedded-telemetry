# WiFi and MQTT Transport

Version 1.1 adds an optional WiFi transport while preserving the proven USB/UART path.

## Architecture

```text
BME280 + IMU
     |
   ESP8285
   /     \
UART     WiFi
 |        |
CP2102   MQTT broker
 |        |
 +---- Ground Station
```

The same telemetry packet and command protocol are used on both transports. This keeps CRC validation, fault injection, state handling, logging, and diagnostics transport-independent.

## MQTT Topics

For device ID `esp8285-node`:

```text
embedded-telemetry/esp8285-node/telemetry
embedded-telemetry/esp8285-node/command
embedded-telemetry/esp8285-node/response
embedded-telemetry/esp8285-node/availability
```

`availability` is retained and publishes `online` when connected. MQTT Last Will publishes `offline` when the broker detects an unexpected disconnect.

## Firmware Configuration

Copy:

```text
include/wifi_secrets.example.h
```

to:

```text
include/wifi_secrets.h
```

and fill in the local values:

```cpp
constexpr const char *SSID = "YOUR_WIFI_SSID";
constexpr const char *PASSWORD = "YOUR_WIFI_PASSWORD";
constexpr const char *MQTT_HOST = "192.168.1.10";
constexpr uint16_t MQTT_PORT = 1883;
constexpr const char *MQTT_USER = "";
constexpr const char *MQTT_PASSWORD = "";
constexpr const char *DEVICE_ID = "esp8285-node";
```

`include/wifi_secrets.h` is gitignored and must never be committed.

If the file is absent, firmware still builds and runs with WiFi transport disabled.

## Ground Station over MQTT

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Launch against a broker on the local network:

```powershell
python -m ground_station.ground_station --mqtt 192.168.1.10
```

Optional arguments:

```text
--mqtt-port 1883
--device esp8285-node
--mqtt-user USERNAME
--mqtt-password PASSWORD
```

The existing dashboard, commands, CRC validation, fault injection, logging, and plots are reused without a separate WiFi UI.

## Recommended First Deployment

Use a Mosquitto broker on the same local network as both the ESP8285 and ground-station computer. Start with an isolated/private LAN and no internet exposure.

For deployment beyond a trusted LAN, add authenticated TLS rather than exposing plaintext MQTT port 1883 to the internet.

## Why MQTT

MQTT provides a clean transition from a tethered USB development tool to a distributed telemetry system. Multiple consumers can subscribe to telemetry later, including a ground station, database logger, web dashboard, or fleet service, without changing sensor acquisition code.
