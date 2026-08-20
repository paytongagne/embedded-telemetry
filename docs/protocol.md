# Serial Protocol

## Transport

- UART over CP2102 USB bridge
- 115200 baud
- UTF-8/ASCII-compatible line protocol
- one message per newline

## Telemetry

Telemetry begins with `TEL,<sequence>` followed by comma-separated `KEY=VALUE` fields.

```text
TEL,42,TIME=12345,TEMP=25.50,PRESS=980.10,HUM=31.20,AX=0.010,AY=-0.020,AZ=0.999,GX=0.10,GY=0.20,GZ=-0.30,BME=OK,IMU=OK,AUX=PRESENT,I2C_ERR=0,RECOVERY=0,BME_FAIL=0,IMU_FAIL=0,STATUS=NORMAL,CRC=ABCD
```

### Core fields

| Field | Meaning |
| --- | --- |
| sequence | monotonically increasing packet sequence number |
| `TIME` | device uptime in milliseconds |
| `TEMP` | BME temperature in Celsius |
| `PRESS` | pressure in hPa |
| `HUM` | relative humidity percent |
| `AX/AY/AZ` | acceleration in g |
| `GX/GY/GZ` | angular rate in deg/s |
| `BME` | `OK` or `FAULT` |
| `IMU` | `OK` or `FAULT` |
| `AUX` | `PRESENT` or `ABSENT` |
| `I2C_ERR` | cumulative low-level I2C errors |
| `RECOVERY` | successful sensor recoveries |
| `BME_FAIL` | BME failure count |
| `IMU_FAIL` | IMU failure count |
| `STATUS` | `NORMAL`, `DEGRADED`, or `FAULT` |
| `CRC` | CRC-16/CCITT in four-digit hexadecimal |

During degraded operation, sensor measurement fields may be omitted. Health/state fields remain present so the receiver can distinguish an intentional degraded packet from a malformed packet.

## CRC

Firmware v0.6 uses CRC-16/CCITT with:

- initial value: `0xFFFF`
- polynomial: `0x1021`
- no final XOR

The CRC is calculated over all packet characters before the final `,CRC=XXXX` field.

The desktop parser rejects a packet when a CRC field exists but does not validate. Packets without CRC are still accepted as legacy development traffic.

## Commands

```text
CMD,STATUS
CMD,PAUSE
CMD,RESUME
CMD,SET_RATE,<milliseconds>
CMD,INJECT_FAULT,IMU
CMD,INJECT_FAULT,BME
CMD,CLEAR_FAULTS
CMD,RESET
```

`SET_RATE` accepts 100 through 10000 milliseconds.

## Acknowledgements

```text
ACK,STATUS
ACK,PAUSE
ACK,RESUME
ACK,SET_RATE,500
ACK,INJECT_FAULT,IMU
ACK,CLEAR_FAULTS
ACK,RESET
```

Commands that change health or timing state are followed by a `STATUS` response where useful.

## Status response

```text
STATUS,STATE=NORMAL,BME=OK,IMU=OK,AUX=PRESENT,PAUSED=0,RATE_MS=500,I2C_ERR=0,RECOVERY=0,RECOVERY_ATTEMPTS=0,BME_FAIL=0,IMU_FAIL=0,FW=0.6.0
```

## Errors

Errors begin with `ERR`.

```text
ERR,BAD_FORMAT,<input>
ERR,MISSING_VALUE,SET_RATE
ERR,RATE_RANGE,100-10000
ERR,BAD_TARGET,<target>
ERR,UNKNOWN_COMMAND,<command>
```
