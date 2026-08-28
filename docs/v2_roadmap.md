# Ground Station v2 Roadmap

## Implemented in the current v2 branch

- multi-transport connection manager
- persistent SQLite sessions
- history browser and replay
- session CSV export
- derived acceleration/gyro engineering metrics
- deterministic alert engine
- automated fault-recovery validation
- exportable HTML validation reports

## Next engineering milestones

### Fault black-box capture
Keep a rolling pre-fault buffer and preserve a post-fault window when the system enters `FAULT`. Store the capture with the session, device state, and event context.

### Session comparison / regression analysis
Compare two recorded sessions by packet loss, recovery timing, temperature range, acceleration RMS, gyro RMS, error counters, and firmware version. Use this to flag performance regressions between firmware builds.

### High-rate IMU mode + FFT
Add a burst acquisition path for higher-rate inertial sampling. Separate high-rate acquisition from the normal low-rate dashboard telemetry stream. Analyze RMS vibration, dominant frequency, spectral peaks, and changes from a known-good baseline.

### Device management
Expose device ID, firmware/build version, protocol version, reset reason, boot count, network identity, RSSI, telemetry rate, calibration offsets, and persisted configuration.

### Configuration / calibration
Allow safe runtime configuration of thresholds and sampling behavior. Add guided IMU zeroing/calibration and retain calibration metadata with sessions.

### OTA firmware workflow
Add image metadata, integrity validation, update progress, reboot verification, and a recovery strategy before considering remote firmware delivery complete.

### Multi-device fleet mode
Maintain a device registry and simultaneous status view with node identity, transport, firmware, last-seen time, state, alert count, and session history.

### Statistical baseline / anomaly detection
Start with explainable baseline statistics and rolling z-score/envelope detection. Later evaluate multivariate models on captured real-world sessions. Always surface contributing metrics rather than a black-box score alone.

### Product packaging
Build a Windows executable/installer, release artifacts, versioned firmware binaries, screenshots, sample sessions, and a no-hardware demo workflow.

## Design principle

Every major feature should be backed by one or more of: automated tests, recorded test evidence, hardware validation, or clearly documented simulator validation. The goal is a credible engineering platform rather than a feature checklist.
