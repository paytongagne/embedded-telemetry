# Embedded Telemetry and Ground Station Platform

A multi-sensor embedded telemetry platform built around an ESP8285 development board with onboard environmental and inertial sensing, a UART telemetry link, and a Python ground station for live monitoring, visualization, and logging.

## Features

- ESP8285-based custom firmware
- Environmental telemetry via BME280
  - Temperature
  - Pressure
  - Humidity
- Inertial telemetry via MPU-9250 compatible IMU
  - Accelerometer X/Y/Z
  - Gyroscope X/Y/Z
- UART telemetry over CP2102 USB-to-UART bridge
- Python ground station
  - Live serial ingestion
  - Dashboard output
  - Real-time graphing
  - CSV logging
- Sensor and device health monitoring
- Expandable test suite

## Hardware Characterization

The board was initially undocumented, so hardware support was developed through direct characterization.

### Identified Components
- Main MCU: ESP8285N08
- USB/UART bridge: CP2102
- I2C devices:
  - `0x76` -> BME280
  - `0x68` -> MPU-9250 compatible IMU
  - `0x29` -> unidentified auxiliary device

## Telemetry Format

Current telemetry uses a readable key-value format over serial:

```text
TEL,49,TIME=49747,TEMP=28.78,PRESS=979.26,HUM=29.45,AX=-0.097,AY=-0.938,AZ=0.209,GX=0.05,GY=0.11,GZ=-0.32,STATUS=NORMAL
