# Architecture

## Design goals

The project is split so that hardware acquisition, device health, transport/protocol logic, and desktop presentation can evolve independently.

## Firmware layers

```text
main.cpp
  |
  +-- SensorManager -------- sensors.cpp
  |      |
  |      +-- BME280
  |      +-- MPU-compatible IMU
  |      +-- AUX presence detection
  |      +-- health checks / recovery counters
  |
  +-- Command processor ---- command.cpp
  |      +-- STATUS
  |      +-- PAUSE / RESUME
  |      +-- SET_RATE
  |      +-- fault injection / clear
  |      +-- RESET
  |
  +-- Telemetry ------------ telemetry.cpp
  |      +-- packet construction
  |      +-- system state
  |      +-- health counters
  |      +-- CRC-16/CCITT
  |
  +-- System state --------- system_state.cpp
         +-- NORMAL
         +-- DEGRADED
         +-- FAULT
```

`main.cpp` only coordinates these modules. Sensor/register details and command parsing are intentionally kept out of the main loop.

## Ground-station layers

```text
serial_manager.py / demo_serial.py
                |
                v
            parser.py
                |
        +-------+-------+
        |               |
     stats.py         logger.py
        |               |
        +-------+-------+
                |
              app.py
```

The serial reader places complete lines into queues. The Qt GUI drains those queues on the GUI thread, preventing background serial activity from directly mutating widgets.

## Data flow

1. Sensors are sampled by the ESP8285.
2. Health state is included in every telemetry packet.
3. The packet is protected with CRC-16/CCITT.
4. UART carries telemetry through the CP2102 USB bridge.
5. The Python parser validates CRC and converts numeric fields.
6. Statistics track packet rate, sequence gaps, and extrema.
7. The UI renders values and plots while the logger independently writes session data.
8. Commands travel in the reverse direction over the same serial connection.

## Reliability choices

- telemetry timing is non-blocking
- command parsing remains responsive while telemetry is active
- periodic health checks are separated from per-packet sensor reads
- sensor recovery attempts do not change the external command protocol
- injected faults are separated from physical sensor state
- missing fields are valid during degraded operation
- the ground station accepts legacy non-CRC packets for development compatibility, but v0.6 firmware emits CRC-protected packets
