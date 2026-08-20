# Fault Management

## State model

The supported BME and IMU health states determine the system state.

| BME | IMU | System state |
| --- | --- | --- |
| OK | OK | `NORMAL` |
| OK | FAULT | `DEGRADED` |
| FAULT | OK | `DEGRADED` |
| FAULT | FAULT | `FAULT` |

The unidentified auxiliary I2C device at `0x29` is reported for diagnostics but does not determine the system state.

## Physical health monitoring

The sensor manager periodically checks known identity registers. If communication or identity validation fails, the corresponding sensor is marked offline and a reinitialization attempt is made.

Tracked counters include:

- low-level I2C errors
- recovery attempts
- successful recoveries
- BME failures
- IMU failures

These counters are exposed through both `STATUS` responses and telemetry packets.

## Fault injection

Fault injection allows degraded behavior to be demonstrated without physically disconnecting hardware.

```text
CMD,INJECT_FAULT,IMU
CMD,INJECT_FAULT,BME
CMD,CLEAR_FAULTS
```

Injected faults affect externally reported health and sensor sampling while leaving the underlying physical-online state intact. This separation allows `CLEAR_FAULTS` to recover immediately when the real device is healthy.

## Ground-station behavior

The desktop application:

- highlights system state and individual sensor health
- removes stale sensor values when that sensor enters `FAULT`
- keeps plotting unaffected sensors in degraded mode
- distinguishes transport `STALE` from device `FAULT`
- records command/status transitions in the event log
- keeps raw serial traffic available for diagnosis

## Transport versus device health

A stale serial stream is not treated as a sensor failure. The ground station tracks transport state independently:

```text
NO DATA -> WAITING -> LIVE
                    -> PAUSED
                    -> STALE
```

The stale threshold scales with the commanded telemetry period so intentionally slow telemetry is not incorrectly classified as a transport fault.

## Recovery strategy

The current recovery strategy is intentionally bounded and non-blocking at the architecture level:

1. detect identity/read failure
2. mark the sensor unavailable
3. record the failure
4. attempt device reinitialization during health service
5. record successful recovery
6. return to `NORMAL` once both required sensors are healthy

A future hard-watchdog reset policy can be added for unrecoverable MCU-level hangs without changing the telemetry or command protocol.
