# Embedded Telemetry & Fault Management Platform

**Version 2.0.0-dev** | ESP8285 + C++ firmware + Python/PySide6 engineering ground station

A hardware-backed embedded telemetry, diagnostics, and validation platform that acquires environmental and inertial sensor data over I2C, performs health monitoring and fault recovery, streams CRC-protected telemetry over USB or WiFi, and provides a desktop engineering workstation for live monitoring, persistent session history, replay, alerts, derived motion metrics, and automated fault-recovery validation.

![v1.0 hardware dashboard](docs/images/dashboard-v1.webp)

## v2 Engineering Workstation

The current v2 development branch adds product-level workflows on top of the hardware-validated v1 foundation:

- connection manager for USB/Serial, Direct WiFi, MQTT, and Simulator modes
- automatic SQLite session persistence for validated telemetry, commands, and transport events
- History / Replay session browser with historical temperature and acceleration-magnitude plots
- event timelines and CSV session export
- rolling acceleration and angular-rate magnitude, RMS, variability, and temperature-window metrics
- deterministic warning/critical alert engine for environmental, motion, packet-loss, and device-state conditions
- automated `NORMAL -> DEGRADED -> NORMAL -> DEGRADED -> FAULT -> NORMAL` validation sequence
- exportable HTML validation reports with per-step timing and run metadata

## What It Demonstrates

- embedded C++ architecture on an ESP8285 using PlatformIO/Arduino
- low-level I2C device communication and sensor characterization
- BME280 temperature, pressure, and humidity acquisition
- MPU-9250-compatible acceleration and gyroscope acquisition
- bidirectional UART protocol over a CP2102 USB-UART bridge
- direct WiFi TCP telemetry and optional MQTT transport
- CRC-16/CCITT packet integrity validation
- `NORMAL`, `DEGRADED`, and `FAULT` system-state management
- periodic health checks, error counters, and automatic sensor reinitialization attempts
- safe BME/IMU fault injection and recovery testing
- configurable telemetry rate from 100 ms to 10 s
- packet-loss, malformed-packet, stale-link, and CRC diagnostics
- Python/PySide6 + pyqtgraph real-time ground station
- pitch/roll estimation and an attitude visualization view
- SQLite session history plus CSV/JSON logging
- hardware-free simulator using the same command interface
- automated parser, protocol, simulator, state, statistics, persistence, alert, metric, and validation tests

## System Architecture

```text
                    I2C SENSOR LAYER
             BME280 / IMU / AUX 0x29
                         |
                      ESP8285
          acquisition + health + state machine
                         |
              CRC telemetry + commands
                  /       |       \
                USB      TCP      MQTT
                  \       |       /
                   TRANSPORT LAYER
                         |
              PySide6 Ground Station
     +-----------+-----------+-----------+-----------+
     |           |           |           |           |
 Dashboard   Engineering   History    Validation   Raw/Attitude
                 |           |           |
            RMS/alerts    SQLite      PASS/FAIL
                             |           |
                         Replay/CSV   HTML report
```

## Hardware Characterization

| Component | Characterized result |
| --- | --- |
| MCU | ESP8285N08, 1 MB embedded flash |
| USB-UART | Silicon Labs CP2102 |
| Environmental sensor | BME280 at `0x76` |
| IMU | MPU-9250-compatible device at `0x68`, `WHO_AM_I=0x71` |
| Auxiliary device | Responds at `0x29`; intentionally left unidentified |

## Ground Station

Install dependencies:

```powershell
python -m pip install -r requirements.txt
```

Launch the v2 connection manager:

```powershell
python -m ground_station.ground_station
```

Power-user launch modes remain available:

```powershell
python -m ground_station.ground_station --demo
python -m ground_station.ground_station --wifi 192.168.1.50
python -m ground_station.ground_station --mqtt 192.168.1.10
```

The application provides:

- live temperature, pressure, humidity, acceleration, and angular-rate plots
- BME280, IMU, and auxiliary-device health indicators
- pitch and roll estimation
- packet count, average packet rate, packet loss, malformed-packet, CRC, and stale-link diagnostics
- firmware version, telemetry interval, I2C errors, recoveries, and sensor-failure counters
- command acknowledgements and raw RX/TX inspection
- persistent session database at `data/telemetry.db`
- historical session browsing and replay
- derived motion metrics and alert tracking
- automated fault-state validation and HTML evidence reports

## Firmware

Build:

```powershell
python -m platformio run
```

Upload:

```powershell
python -m platformio run -t upload
```

On the characterized board, entering the ESP8266/ESP8285 bootloader may require holding `USR` while resetting before upload.

## Command Protocol

Commands are newline-terminated ASCII messages.

```text
CMD,STATUS
CMD,PAUSE
CMD,RESUME
CMD,SET_RATE,500
CMD,INJECT_FAULT,IMU
CMD,INJECT_FAULT,BME
CMD,CLEAR_FAULTS
CMD,RESET
```

## Telemetry Protocol

Example packet:

```text
TEL,42,TIME=12345,TEMP=25.50,PRESS=980.10,HUM=31.20,AX=0.010,AY=-0.020,AZ=0.999,GX=0.10,GY=0.20,GZ=-0.30,BME=OK,IMU=OK,AUX=PRESENT,I2C_ERR=0,RECOVERY=0,RECOVERY_ATTEMPTS=0,BME_FAIL=0,IMU_FAIL=0,STATUS=NORMAL,CRC=ABCD
```

CRC-16/CCITT is calculated over the packet before the final `CRC` field. The ground station rejects packets with an invalid CRC while remaining compatible with legacy development packets that omit CRC.

## Fault Management

```text
                 sensor loss
NORMAL ------------------------------> DEGRADED
  ^                                      |
  |                                      | second critical sensor loss
  | recovery                             v
  +----------------------------------- FAULT
```

The v2 Validation tab automates these transitions using the safe injected-fault path and records per-step timing for later test evidence.

## Validation

Run the Python test suite:

```powershell
python -m unittest discover -s test -v
```

Build the embedded firmware:

```powershell
python -m platformio run
```

The v1.0 hardware smoke test verified live BME280 and IMU telemetry, CRC validation, zero packet loss during the observed test session, bidirectional commands, telemetry-rate changes, pause/resume, `NORMAL -> DEGRADED -> FAULT -> NORMAL` transitions, and fault clearing on the characterized ESP8285 board.

## Road to v2.0

The remaining top-end milestones are high-rate IMU/FFT analysis, black-box fault capture, session-to-session regression comparison, device configuration/calibration, richer network diagnostics, OTA firmware delivery, multi-device fleet monitoring, statistical anomaly detection, and a packaged Windows release.

## Scope

This is an engineering prototype and portfolio platform, not a calibrated measurement instrument, safety-certified controller, or production security appliance. Deployment outside a development environment requires application-specific calibration, electrical protection, secure transport configuration, enclosure/power design, and validation.
