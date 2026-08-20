# Testing and Validation

## Python tests

Run from the repository root:

```powershell
python -m unittest discover -s test -v
```

The suite covers parser behavior, CRC validation, command construction, command simulation, state transitions, packet loss, rate statistics, malformed telemetry, and the hardware-free simulator.

## Python syntax validation

```powershell
python -m compileall -q ground_station test
```

This catches syntax errors across the desktop code even when a GUI is not launched.

## Firmware build

```powershell
python -m platformio run
```

The firmware build validates all C++ modules for the configured ESP8285 target.

## Simulator smoke test

No board is required:

```powershell
python -m ground_station.ground_station --demo
```

The simulator exercises the same command, status, CRC, rate, pause/resume, and fault-state paths used by the physical device.

## v1.0 hardware smoke test

The v1.0 feature set was exercised on the characterized physical board. The observed validation session confirmed:

1. CP2102 serial connection on COM3
2. live BME280 temperature, pressure, and humidity data
3. live MPU-compatible accelerometer and gyroscope data
4. live pitch/roll updates
5. `NORMAL` and `LIVE` status during healthy operation
6. valid CRC telemetry
7. zero observed packet loss during the captured validation session
8. zero observed I2C errors during the captured validation session
9. `CMD,STATUS` acknowledgement and status response
10. pause/resume command handling
11. runtime telemetry-rate changes
12. IMU fault injection producing `DEGRADED`
13. simultaneous BME + IMU fault condition producing `FAULT`
14. `CLEAR_FAULTS` returning the system to `NORMAL`

The repository firmware version has now been bumped to `1.0.0`. A final build/upload should be performed before creating the v1.0 Git tag so the physical board reports the same release version as the source tree.

## CI

The repository includes GitHub Actions configuration for two independent checks:

- Python source compilation and unit tests
- PlatformIO ESP8285 firmware build

CI is an additional validation layer and does not replace physical hardware testing.
