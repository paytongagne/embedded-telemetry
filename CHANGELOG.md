# Changelog

## v1.0.0

First portfolio-ready hardware-validated release.

### Firmware

- modularized ESP8285 firmware into sensor, command, telemetry, configuration, and system-state components
- added BME280 environmental acquisition and MPU-compatible IMU acquisition
- added bidirectional UART command handling
- added configurable telemetry interval from 100 ms to 10 s
- added `NORMAL`, `DEGRADED`, and `FAULT` state management
- added BME and IMU fault injection
- added periodic sensor health verification and automatic reinitialization attempts
- added I2C error, sensor failure, recovery-attempt, and successful-recovery counters
- added CRC-16/CCITT telemetry integrity protection

### Ground Station

- added compact real-time environmental and motion dashboard
- added Fahrenheit presentation while retaining Celsius in the wire protocol
- added BME/IMU/AUX health indicators
- added pitch and roll estimation
- added attitude visualization with a 2D fallback
- added live/stale/paused transport-state indication
- added packet-loss, malformed-packet, CRC, and average-rate diagnostics
- added raw RX/TX serial view
- added telemetry/event logging and JSON session summaries
- added command controls for status, pause, resume, telemetry rate, fault injection, fault clearing, statistics reset, and device reset
- added connection-aware control enable/disable behavior

### Testing and Tooling

- added hardware-free device simulator
- added tests for telemetry parsing and CRC validation
- added command/protocol tests
- added simulated fault/state transition tests
- added packet-loss and packet-rate statistics tests
- added Python syntax validation and PlatformIO firmware build workflow configuration
- added architecture, hardware, protocol, fault-management, testing, and real-world use-case documentation

### Hardware Validation

The v1.0 smoke test on the characterized ESP8285 board verified:

- BME280 and MPU-compatible IMU live telemetry
- `NORMAL` operation with zero observed packet loss during the test session
- valid CRC telemetry
- status requests and command acknowledgements
- pause/resume
- runtime telemetry-rate changes
- IMU fault injection producing `DEGRADED`
- simultaneous BME + IMU faults producing `FAULT`
- fault clearing returning the platform to `NORMAL`
