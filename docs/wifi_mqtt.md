# WiFi Provisioning and Wireless Telemetry

Version 1.1 adds wireless telemetry while preserving the proven USB/UART path.

## Architecture

```text
BME280 + IMU
     |
   ESP8285
   /     \
UART     WiFi
 |       /   \
CP2102  TCP   MQTT
 |       |      |
 +-------+------+
         |
   Ground Station
```

The same telemetry packet and command protocol are used on every transport. CRC validation, fault injection, state handling, logging, and diagnostics stay transport-independent.

Direct TCP is the normal wireless ground-station path. MQTT is optional and is intended for multi-subscriber logging, dashboards, databases, and later IoT/fleet experiments.

## First-Boot Provisioning

Users do not edit firmware source code to enter WiFi credentials.

When the ESP8285 has no saved wireless configuration, it starts a temporary setup access point named like:

```text
EmbeddedTelemetry-Setup-1A2B3C
```

Connect to that network from a laptop or phone. The WiFiManager captive portal opens automatically on most devices.

The setup form contains:

- WiFi network and password
- device name / device ID
- optional MQTT broker host or IP
- MQTT port
- optional MQTT username and password

After saving, the ESP8266 WiFi stack stores the WiFi credentials and the project stores device/MQTT settings in flash-backed EEPROM.

MQTT can be left blank. A broker is not required for direct wireless telemetry.

## Normal Boot

On later boots the device reconnects to the saved WiFi network and starts a direct telemetry/command server on TCP port `9000`.

USB telemetry remains available at the same time, providing a wired maintenance and recovery path.

## Direct Ground Station

After provisioning, note the IP address shown by the device and launch:

```powershell
python -m ground_station.ground_station --wifi 192.168.1.50
```

The default direct port is `9000`. It can be overridden with:

```text
--wifi-port 9000
```

The dashboard, commands, CRC checks, logging, plots, pause/resume, telemetry-rate control, and fault injection all work over the direct WiFi transport.

## Optional MQTT

If a broker is entered during provisioning, the device also publishes and accepts commands through MQTT.

For device ID `esp8285-node`:

```text
embedded-telemetry/esp8285-node/telemetry
embedded-telemetry/esp8285-node/command
embedded-telemetry/esp8285-node/response
embedded-telemetry/esp8285-node/availability
```

Launch the ground station through MQTT with:

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

MQTT availability is retained. The device publishes `online` when connected and configures a Last Will of `offline` for unexpected disconnects.

## Recommended Deployment

For a normal single-laptop setup, use direct WiFi TCP and leave MQTT blank.

Use MQTT when multiple consumers need the telemetry stream, such as a desktop ground station plus a database logger or web dashboard.

Keep development deployments on a private LAN. For any internet-facing deployment, add authenticated encryption rather than exposing either the direct TCP port or plaintext MQTT to the public internet.
