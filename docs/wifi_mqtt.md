# WiFi, Provisioning, and MQTT Transport

Version 1.1 adds WiFi/MQTT transport while preserving the proven USB/UART path.

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

The same telemetry packet and command protocol are used on both transports. CRC validation, fault injection, state handling, logging, and diagnostics stay transport-independent.

## First-Boot Provisioning

Users no longer edit firmware source code to enter WiFi credentials.

When the ESP8285 has no saved wireless configuration, it starts a temporary setup access point named like:

```text
EmbeddedTelemetry-Setup-1A2B3C
```

Connect to that network from a laptop or phone. The WiFiManager captive portal opens automatically on most devices. If it does not, open the gateway page offered by the setup network.

The setup form contains:

- WiFi network and password
- MQTT broker host or IP
- MQTT port
- optional MQTT username and password
- device name / device ID

After saving, WiFiManager stores the WiFi credentials using the ESP8266 WiFi stack and this project stores the MQTT/device fields in ESP flash-backed EEPROM. The device then joins the selected network and starts MQTT service.

No WiFi password or MQTT credential file is required in the repository.

## Normal Boot

On later boots the device loads the saved MQTT/device configuration and reconnects using the stored WiFi credentials. If the saved WiFi network is unavailable, WiFiManager can expose the setup portal again after the normal connection attempt fails.

USB telemetry remains available even when wireless provisioning times out or the broker is unavailable.

## MQTT Topics

For device ID `esp8285-node`:

```text
embedded-telemetry/esp8285-node/telemetry
embedded-telemetry/esp8285-node/command
embedded-telemetry/esp8285-node/response
embedded-telemetry/esp8285-node/availability
```

`availability` is retained and publishes `online` when connected. MQTT Last Will publishes `offline` when the broker detects an unexpected disconnect.

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

The existing dashboard, commands, CRC validation, fault injection, logging, and plots are reused without a separate telemetry UI.

## Recommended First Deployment

Use a Mosquitto broker on the same private LAN as both the ESP8285 and ground-station computer. Start with no internet exposure.

For deployment beyond a trusted LAN, use authenticated TLS rather than exposing plaintext MQTT port 1883 to the internet.

## Why MQTT

MQTT provides a clean transition from a tethered USB development tool to a distributed telemetry system. Multiple consumers can subscribe to telemetry later, including a ground station, database logger, web dashboard, or fleet service, without changing sensor acquisition code.
