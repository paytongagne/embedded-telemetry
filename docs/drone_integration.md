# Drone Integration Roadmap

The telemetry board is best treated as a payload/monitoring subsystem, not as the primary flight controller.

## Recommended Role

```text
Flight Controller  -> motors / stabilization / failsafes
        |
        +---- telemetry interface (optional later)

ESP8285 Telemetry Node
        |
        +---- BME280 environmental sensing
        +---- IMU motion/orientation sensing
        +---- WiFi/MQTT engineering telemetry
        +---- health/fault diagnostics
```

Keeping flight stabilization on a dedicated flight controller prevents experimental telemetry code from becoming flight-critical.

## Useful Flight-Test Data

The existing platform can record:

- temperature, humidity, and pressure
- acceleration and angular velocity
- pitch and roll estimates
- link health and packet loss
- sensor state and fault counters
- telemetry timestamps and session logs

Potential additions for a flight-test payload include GPS position, battery voltage/current, barometric altitude processing, and read-only flight-controller telemetry.

## Development Sequence

1. Validate WiFi/MQTT on the bench.
2. Run the node from a regulated portable power source.
3. Mount it to a stationary frame and check vibration/noise.
4. Mount it to a non-flying moving test platform and validate logs/link behavior.
5. Install it on a small hobby drone as a non-flight-critical payload.
6. Perform low-risk line-of-sight flight tests in accordance with local rules and the aircraft manufacturer's limits.
7. Only after stable operation, consider read-only integration with the flight controller for additional telemetry.

## Engineering Considerations

- use a regulated supply appropriate for the telemetry board
- isolate the node from motor/ESC electrical noise where practical
- secure wiring and connectors against vibration
- keep added mass near the vehicle center of gravity
- verify WiFi range and packet-loss behavior before relying on live telemetry
- retain onboard or ground-station logging because WiFi packets can be lost in flight
- do not use this experimental node as the sole control, navigation, or safety link

This progression turns the current project into a small flight-test instrumentation system while preserving a conventional, independently stabilized aircraft architecture.
