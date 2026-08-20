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

## Hardware smoke test

After a successful build and flash:

1. connect the ground station to the CP2102 COM port
2. confirm `NORMAL`, `BME=OK`, `IMU=OK`, and `LIVE`
3. request status
4. set telemetry rate to 500 ms and verify approximately 2 Hz
5. pause and resume telemetry
6. inject an IMU fault and verify `DEGRADED`
7. clear faults and verify return to `NORMAL`
8. inject a BME fault and confirm environmental fields disappear while IMU data continues
9. verify raw serial traffic and event log entries
10. allow the session to run long enough to confirm packet-loss and CRC diagnostics remain clean

## Simulator smoke test

No board is required:

```powershell
python -m ground_station.ground_station --demo
```

The simulator exercises the same command, status, CRC, rate, pause/resume, and fault-state paths used by the physical device.

## CI

GitHub Actions performs two independent checks:

- Python source compilation and unit tests
- PlatformIO ESP8285 firmware build

This prevents desktop-only changes from silently breaking the firmware and vice versa.
