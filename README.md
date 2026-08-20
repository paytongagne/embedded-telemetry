# Embedded Telemetry & Fault Management Platform

An ESP8285-based embedded telemetry system that acquires environmental and inertial sensor data over I2C, streams validated telemetry over UART, and provides a Python/PySide6 ground station for real-time monitoring, command/control, fault injection, logging, and diagnostics.

## Highlights

- ESP8285 firmware written in C++ with PlatformIO/Arduino
- BME280 environmental telemetry: temperature, pressure, humidity
- MPU-9250-compatible IMU telemetry: 3-axis acceleration and gyroscope
- Auxiliary I2C device detection at `0x29` without assuming an unsupported device identity
- Bidirectional UART command protocol over a CP2102 USB-UART bridge
- Runtime telemetry-rate control from 100 ms to 10 s
- `NORMAL`, `DEGRADED`, and `FAULT` system states
- BME/IMU fault injection and recovery commands
- Periodic sensor health checks and automatic reinitialization attempts
- I2C, sensor-failure, and recovery counters
- CRC-16/CCITT telemetry integrity validation
- Packet-loss and malformed-packet detection
- PySide6 + pyqtgraph desktop ground station
- Fahrenheit display while preserving raw Celsius telemetry/logging
- Live pitch/roll derived from accelerometer data
- Raw serial traffic view, CSV event/telemetry logging, and JSON session summaries
- Built-in hardware-free simulator with the same command interface
- Automated Python tests and PlatformIO firmware builds in GitHub Actions

## System Architecture

```text
                     I2C
       +-----------------------------+
       |              |              |
    BME280      MPU-compatible    AUX 0x29
       |              |              |
       +--------------+--------------+
                      |
                  ESP8285
             sensor + health layer
                      |
            telemetry / commands
                      |
                  UART 115200
                      |
              CP2102 USB bridge
                      |
                      v
       Python / PySide6 Ground Station
       +-----------+----------+----------+
       |           |          |          |
    Live plots   Logging   Diagnostics  Control
```

More detail is available in [`docs/architecture.md`](docs/architecture.md).

## Hardware Characterization

The current board has been characterized as:

| Component | Result |
| --- | --- |
| MCU | ESP8285N08, 1 MB embedded flash |
| USB-UART | Silicon Labs CP2102 |
| Environmental sensor | BME280 at `0x76` |
| IMU | MPU-9250-compatible device at `0x68`, `WHO_AM_I=0x71` |
| Auxiliary device | Responds at `0x29`, intentionally left unidentified |

See [`docs/hardware.md`](docs/hardware.md) for the characterization approach and constraints.

## Ground Station

The dashboard provides:

- live temperature, pressure, humidity, acceleration, and angular-rate plots
- compact telemetry and sensor-health cards
- pitch/roll estimation
- packet count, average packet rate, packet loss, malformed packet count
- live/stale/paused transport status
- firmware version, telemetry rate, I2C errors, recoveries, and sensor-failure counters
- command acknowledgements and device status responses
- raw serial RX/TX inspection

### Run with hardware

```powershell
python -m pip install -r requirements.txt
python -m ground_station.ground_station
```

Select the CP2102 COM port and connect.

### Run without hardware

```powershell
python -m ground_station.ground_station --demo
```

The built-in simulator produces CRC-protected telemetry and responds to the same pause, resume, rate, status, and fault-injection commands.

## Firmware

Build:

```powershell
python -m platformio run
```

Upload:

```powershell
python -m platformio run -t upload
```

For this board, entering the ESP8266/ESP8285 bootloader may require holding the board's `USR` button while resetting the device before upload.

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

Examples:

```text
ACK,SET_RATE,500
STATUS,STATE=NORMAL,BME=OK,IMU=OK,AUX=PRESENT,PAUSED=0,RATE_MS=500,...
ERR,RATE_RANGE,100-10000
```

See [`docs/protocol.md`](docs/protocol.md).

## Telemetry Protocol

Example packet:

```text
TEL,42,TIME=12345,TEMP=25.50,PRESS=980.10,HUM=31.20,AX=0.010,AY=-0.020,AZ=0.999,GX=0.10,GY=0.20,GZ=-0.30,BME=OK,IMU=OK,AUX=PRESENT,I2C_ERR=0,RECOVERY=0,BME_FAIL=0,IMU_FAIL=0,STATUS=NORMAL,CRC=ABCD
```

The CRC is calculated over the complete packet before the final `,CRC=XXXX` field. Legacy packets without CRC remain parseable by the ground station for development compatibility.

## Fault Management

```text
                 sensor loss
NORMAL ------------------------------> DEGRADED
  ^                                      |
  |                                      | second critical sensor loss
  | recovery                             v
  +----------------------------------- FAULT
```

The firmware periodically verifies sensor communication. Failed sensors are marked unhealthy and recovery is attempted without blocking the command processor. Injected faults are kept separate from physical device state so fault behavior can be demonstrated safely.

See [`docs/fault_management.md`](docs/fault_management.md).

## Project Structure

```text
embedded-telemetry/
├── include/
│   ├── command.h
│   ├── config.h
│   ├── sensors.h
│   ├── system_state.h
│   └── telemetry.h
├── src/
│   ├── command.cpp
│   ├── main.cpp
│   ├── sensors.cpp
│   ├── system_state.cpp
│   └── telemetry.cpp
├── ground_station/
│   ├── app.py
│   ├── demo_serial.py
│   ├── logger.py
│   ├── parser.py
│   ├── protocol.py
│   ├── serial_manager.py
│   └── stats.py
├── test/
├── docs/
├── platformio.ini
└── requirements.txt
```

## Tests

```powershell
python -m unittest discover -s test -v
```

Tests cover telemetry parsing, CRC validation, command construction, simulated command handling, state transitions, packet loss, malformed packets, and packet-rate statistics.

GitHub Actions also performs a PlatformIO firmware build on pushes and pull requests.

## Current Version

Firmware: **v0.6.0**

The current focus is reliability, testability, and clean separation between sensor acquisition, health management, telemetry, commands, and UI presentation.
