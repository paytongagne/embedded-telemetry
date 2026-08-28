# Drone Companion Telemetry Concept and Flight View

## Purpose

The ESP8285 telemetry PCB is intended to ride inside a compact X-frame quadcopter as a **companion monitoring module**, not as the primary flight controller. The existing flight controller remains responsible for stabilization, motor mixing, failsafes, and safety-critical flight control. The telemetry PCB measures inertial/environmental behavior, records health information, and streams diagnostic data to the desktop ground station.

## Airframe concept

- compact 3- to 5-inch-class X-frame quadcopter
- four brushless motors and four ESC channels controlled by a dedicated flight controller
- LiPo battery sized for the chosen propulsion system
- telemetry PCB mounted in the center stack near the airframe center of gravity
- soft vibration-damping standoffs between the telemetry PCB and frame
- PCB mounted with a known body-axis orientation

## Coordinate convention

The project uses the following body-frame convention in Flight View:

- **+X = forward / nose**
- **+Y = lateral / right**
- **+Z = up**

The physical PCB should be mounted so its interpreted sensor axes match this convention. If the final PCB orientation differs, the firmware or ground-station axis mapping should be changed explicitly rather than compensating mentally during testing.

## What the PCB monitors

- accelerometer X/Y/Z
- gyroscope X/Y/Z
- BME280 pressure, temperature, and humidity
- pitch and roll derived from gravity-referenced accelerometer data
- roll, pitch, and yaw angular rates
- device/system health states
- packet integrity and link diagnostics
- fault injection / recovery behavior
- black-box fault captures

## Flight View visualization

The ground station renders a 3D quadcopter with:

- four arms, motors, and propeller discs
- highlighted center-mounted telemetry PCB
- forward/nose marker
- body-fixed X/Y/Z axes
- fixed world axes and ground grid
- pitch and roll motion
- angular-rate rings around the X/Y/Z axes
- dynamic-acceleration vector
- bounded relative movement trail
- IMU-derived short-window forward/lateral displacement estimate
- barometric relative-altitude estimate

## Position-estimation limitation

The current sensor set is **not a complete navigation solution**.

Pitch and roll can be gravity-referenced, but absolute yaw/heading is not available without a magnetometer or another external heading source. Long-duration X/Y position cannot be recovered accurately by double-integrating an accelerometer because bias and vibration accumulate rapidly.

For that reason Flight View labels its dimensional movement as **RELATIVE / ESTIMATED**:

- X/Y: short-window IMU integration with deadband, damping, stationary detection, bounded drift, and manual reference reset
- Z: pressure-derived altitude relative to the first valid pressure sample
- yaw: angular rate only; no false absolute heading is displayed

These values are for visualization, diagnostics, and test interpretation. They must not be used as flight-control position feedback.

## Future navigation upgrade path

A later drone revision can add one or more external references:

- magnetometer for heading
- GPS for outdoor position/velocity
- optical flow for low-altitude relative motion
- UWB anchors for indoor positioning
- flight-controller telemetry containing fused attitude/navigation estimates

When one of those sources is integrated, Flight View can switch from estimated local movement to a true navigation mode while keeping the current diagnostic mode available for comparison.
