# Hardware Characterization

## Board

The development board uses an ESP8285N08 microcontroller and CP2102 USB-to-UART bridge. The ESP8285 was identified through the Espressif bootloader tooling as an ESP8266-family device with 1 MB embedded flash and a 26 MHz crystal.

The original 1 MB factory flash image was backed up before replacing the firmware.

## USB / programming

Windows enumerates the board through the Silicon Labs CP210x driver. The development setup currently uses 115200 baud UART.

The board exposes `USR` and `RST` buttons. Entering the bootloader for flashing can require holding `USR` while resetting the board so GPIO0 is sampled low during reset.

## I2C characterization

The original firmware scan exposed three responding addresses:

| Address | Characterization | Evidence |
| --- | --- | --- |
| `0x76` | BME280 | chip ID register returned `0x60` |
| `0x68` | MPU-9250-compatible IMU | `WHO_AM_I` register `0x75` returned `0x71` |
| `0x29` | unidentified auxiliary device | responds to I2C address probe |

The auxiliary device is intentionally reported only as present/absent. An early VL53L0X hypothesis did not initialize successfully, so the project does not claim a specific device identity for `0x29`.

## BME280

The BME280 supplies:

- temperature in degrees Celsius at the firmware/protocol layer
- pressure in hPa
- relative humidity in percent

The desktop UI converts temperature to Fahrenheit for display while retaining raw Celsius values in telemetry logs.

## IMU

The MPU-compatible device is configured by clearing its sleep state through power-management register `0x6B`. Raw accelerometer and gyroscope words are read from the standard MPU register map.

Current conversions assume the reset/default full-scale settings:

- accelerometer: `16384 LSB/g`
- gyroscope: `131 LSB/(deg/s)`

Pitch and roll shown by the desktop application are gravity-based estimates calculated from the accelerometer and are not a full attitude solution.

## Health checks

The firmware periodically verifies:

- BME280 chip identity at register `0xD0`
- MPU identity at register `0x75`
- continued presence of the auxiliary I2C address

If a supported sensor becomes unavailable, the sensor manager records the failure and attempts reinitialization during later health service cycles.
