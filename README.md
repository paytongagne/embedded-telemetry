# Embedded Telemetry & Fault Management Platform

**Version 1.0.0** | ESP8285 + C++ firmware + Python/PySide6 ground station

A hardware-validated embedded telemetry platform that acquires environmental and inertial sensor data over I2C, performs device health monitoring and fault recovery, streams CRC-protected telemetry over UART, and exposes a desktop ground station for real-time visualization, command/control, diagnostics, logging, and fault injection.

## What It Demonstrates

- embedded C++ architecture on an ESP8285 using PlatformIO/Arduino
- low-level I2C device communication and sensor characterization
- BME280 temperature, pressure, and humidity acquisition
- MPU-9250-compatible acceleration and gyroscope acquisition
- bidirectional UART protocol over a CP2102 USB-UART bridge
- CRC-16/CCITT packet integrity validation
- `NORMAL`, `DEGRADED`, and `FAULT` system-state management
- periodic health checks, error counters, and automatic sensor reinitialization attempts
- safe BME/IMU fault injection and recovery testing
- configurable telemetry rate from 100 ms to 10 s
- packet-loss, malformed-packet, stale-link, and CRC diagnostics
- Python/PySide6 + pyqtgraph real-time ground station
- pitch/roll estimation and an attitude visualization view
- CSV telemetry/event logging and JSON session summaries
- hardware-free simulator using the same ground-station command interface
- automated parser, protocol, simulator, state, and statistics tests

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
          acquisition + health layer
                      |
           state / telemetry / commands
                      |
                CRC-protected UART
                      |
              CP2102 USB bridge
                      |
                      v
       Python / PySide6 Ground Station
       +------------+-----------+------------+
       |            |           |            |
    Live plots   Logging   Diagnostics   Command/Control
```

See [`docs/architecture.md`](docs/architecture.md) for the software architecture.

## Hardware Characterization

| Component | Characterized result |
| --- | --- |
| MCU | ESP8285N08, 1 MB embedded flash |
| USB-UART | Silicon Labs CP2102 |
| Environmental sensor | BME280 at `0x76` |
| IMU | MPU-9250-compatible device at `0x68`, `WHO_AM_I=0x71` |
| Auxiliary device | Responds at `0x29`; intentionally left unidentified |

See [`docs/hardware.md`](docs/hardware.md) for the characterization process and limitations.

## Ground Station

The desktop application provides:

- live temperature, pressure, humidity, acceleration, and angular-rate plots
- Fahrenheit presentation while preserving protocol-native Celsius values
- BME280, IMU, and auxiliary-device health indicators
- pitch and roll estimation
- optional attitude visualization with a 2D fallback
- packet count, average packet rate, packet loss, and malformed-packet tracking
- `LIVE`, `STALE`, and paused transport status
- firmware version, telemetry interval, I2C errors, recoveries, and sensor-failure counters
- CRC validity indication
- command acknowledgements and device status responses
- raw serial RX/TX inspection
- telemetry/event logging and session summaries

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

Demo mode produces CRC-protected telemetry and responds to the same status, pause, resume, rate, and fault-injection commands as the physical device.

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

The firmware periodically verifies sensor communication and attempts reinitialization when a physical sensor becomes unavailable. Injected faults are tracked separately from physical communication state so the state machine can be demonstrated safely.

See [`docs/fault_management.md`](docs/fault_management.md).

## Real-World Uses

In its current USB-connected form, the platform is useful as a small engineering data-acquisition and diagnostics node. Practical applications include:

- environmental + motion monitoring on a laboratory test fixture
- vibration, tilt, and temperature observation on motors, fans, pumps, or other equipment during bench testing
- condition monitoring during prototype electronics or enclosure testing
- orientation and motion telemetry for robotics, small vehicles, or mechatronics prototypes
- sensor and embedded-firmware validation with deliberate fault injection
- a teaching/demo platform for telemetry protocols, state machines, CRCs, recovery logic, and host-device communication
- a base platform for a remote IoT monitor once ESP8285 Wi-Fi transport is added

See [`docs/use_cases.md`](docs/use_cases.md) for realistic deployments, current limits, and upgrade paths.

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
│   ├── attitude.py
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

## Scope

Version 1.0 is a bench/prototype telemetry and fault-management platform. It is not a calibrated measurement instrument, safety system, or industrially certified controller. Deployment outside a development environment would require application-specific calibration, electrical protection, enclosure design, power management, and validation.

## Version

**v1.0.0**
