# Changelog

## v2.0.0-dev

Ground-station productization work in progress.

### Ground Station

- added a multi-transport connection manager for USB/Serial, Direct WiFi, MQTT, and Simulator modes
- added local connection preference persistence using Qt `QSettings`
- added a transport factory so connection modes are configured consistently in one place
- added automatic SQLite session persistence without coupling storage logic into the dashboard
- added session, telemetry, and event tables with firmware, transport, endpoint, packet-count, and timestamp metadata
- added command and transport-event recording for later replay and test analysis
- added a History / Replay tab with recorded-session browsing, historical plots, event timelines, replay speed control, scrubber, synchronized cursors, and CSV export
- added rolling engineering metrics for acceleration magnitude, angular-rate magnitude, RMS, variability, and temperature-window change
- added deterministic edge-triggered alerts for environmental, motion, packet-loss, and device-state conditions
- added an automated fault-recovery validation runner for `NORMAL -> DEGRADED -> NORMAL -> DEGRADED -> FAULT -> NORMAL`
- added HTML validation report generation with step timing and run metadata
- added black-box fault capture with pre-fault, trigger, and post-fault telemetry windows
- added session-to-session regression comparison for motion, temperature, CRC, fault-state, packet-count, and duration metrics
- upgraded dashboard plots with synchronized time axes, crosshair inspection, magnitude traces, threshold references, and responsive downsampling
- replaced the generic aircraft attitude view with a 3D quadcopter Flight View showing the companion PCB, body/world axes, rotation-rate rings, dynamic-acceleration vector, and relative movement trail
- added short-window IMU forward/lateral displacement estimation with drift damping and manual reference reset
- added pressure-derived relative barometric altitude for the Flight View vertical axis
- explicitly labels dimensional movement as relative/estimated and keeps yaw rate-only until an external heading reference is available

### Testing and Tooling

- added connection-factory unit tests
- added SQLite persistence round-trip tests
- added engineering-metric, alert, validation-state-machine, reporting, fault-capture, and session-analysis tests
- added flight-motion estimator tests for stationary behavior, relative translation, barometric altitude, and reference reset
- updated CI test dependencies for MQTT-enabled test coverage
- ignored generated database, export, report, and capture artifacts
- added a drone companion-module and Flight View integration design document

### Next v2 Milestones

- configurable alert thresholds and alert acknowledgement workflow
- high-rate IMU acquisition mode and FFT/vibration analysis
- expanded device/network diagnostics, RSSI, reset reason, and build metadata
- device configuration and calibration workflows
- external navigation input support for magnetometer, GPS, optical flow, UWB, or fused flight-controller telemetry
- OTA firmware update path with image integrity checks
- multi-device/fleet monitoring
- statistical baseline and anomaly-detection layer
- packaged Windows release and installer

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
