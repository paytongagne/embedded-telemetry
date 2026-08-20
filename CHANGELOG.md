# Changelog

## v0.6.0

### Firmware

- split monolithic firmware into configuration, sensors, commands, telemetry, and state modules
- added periodic BME280 and IMU health verification
- added automatic sensor reinitialization attempts and recovery counters
- added I2C, BME failure, IMU failure, recovery-attempt, and recovery-success diagnostics
- added CRC-16/CCITT protection to telemetry packets
- preserved non-blocking command processing and configurable telemetry timing
- retained safe BME/IMU fault injection with `NORMAL`, `DEGRADED`, and `FAULT` states

### Ground station

- compacted telemetry and health cards to prioritize plot area
- added stronger state and sensor-health visualization
- added raw RX/TX serial traffic tab
- added firmware/device diagnostics, session duration, rolling packet rate, and packet-loss percentage
- added stale-telemetry detection that scales with commanded packet rate
- added reset-statistics control and connection-aware command controls
- added BME fault injection control
- added optional OpenGL attitude view with a 2D fallback
- retained Fahrenheit presentation while logging protocol-native Celsius values

### Testing and tooling

- added CRC parser tests
- added packet-loss and rolling-rate tests
- added simulated command/state tests
- added hardware-free telemetry simulator and simulator tests
- added GitHub Actions Python validation and ESP8285 PlatformIO builds
- added requirements, architecture, hardware, protocol, fault-management, and testing documentation
