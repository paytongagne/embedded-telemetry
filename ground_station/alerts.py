from dataclasses import dataclass


@dataclass(frozen=True)
class Alert:
    key: str
    severity: str
    message: str
    value: float | str | None = None
    threshold: float | str | None = None


class AlertEngine:
    """Edge-triggered deterministic alarms for telemetry and derived metrics."""

    DEFAULTS = {
        "temperature_high_c": 35.0,
        "humidity_low_percent": 15.0,
        "accel_rms_high_g": 1.35,
        "gyro_rms_high_dps": 40.0,
        "packet_loss_high_percent": 2.0,
    }

    def __init__(self, thresholds=None):
        self.thresholds = dict(self.DEFAULTS)
        if thresholds:
            self.thresholds.update(thresholds)
        self._active = {}

    @property
    def active_alerts(self):
        return list(self._active.values())

    def reset(self):
        self._active.clear()

    def evaluate(self, data, metrics, packet_loss_percent=0.0, stale=False):
        conditions = {}

        temp = data.get("TEMP")
        if temp is not None and float(temp) > self.thresholds["temperature_high_c"]:
            conditions["temperature_high"] = Alert(
                "temperature_high",
                "WARNING",
                "Temperature exceeds configured engineering threshold",
                float(temp),
                self.thresholds["temperature_high_c"],
            )

        humidity = data.get("HUM")
        if humidity is not None and float(humidity) < self.thresholds["humidity_low_percent"]:
            conditions["humidity_low"] = Alert(
                "humidity_low",
                "WARNING",
                "Humidity is below configured engineering threshold",
                float(humidity),
                self.thresholds["humidity_low_percent"],
            )

        accel_rms = metrics.get("accel_rms_g")
        if accel_rms is not None and accel_rms > self.thresholds["accel_rms_high_g"]:
            conditions["accel_rms_high"] = Alert(
                "accel_rms_high",
                "WARNING",
                "Rolling acceleration RMS is elevated",
                accel_rms,
                self.thresholds["accel_rms_high_g"],
            )

        gyro_rms = metrics.get("gyro_rms_dps")
        if gyro_rms is not None and gyro_rms > self.thresholds["gyro_rms_high_dps"]:
            conditions["gyro_rms_high"] = Alert(
                "gyro_rms_high",
                "WARNING",
                "Rolling angular-rate RMS is elevated",
                gyro_rms,
                self.thresholds["gyro_rms_high_dps"],
            )

        if float(packet_loss_percent or 0.0) > self.thresholds["packet_loss_high_percent"]:
            conditions["packet_loss_high"] = Alert(
                "packet_loss_high",
                "WARNING",
                "Packet loss exceeds configured threshold",
                float(packet_loss_percent),
                self.thresholds["packet_loss_high_percent"],
            )

        state = str(data.get("STATUS", data.get("STATE", ""))).upper()
        if state == "DEGRADED":
            conditions["system_degraded"] = Alert(
                "system_degraded", "WARNING", "Device entered DEGRADED state", state, "NORMAL"
            )
        elif state == "FAULT":
            conditions["system_fault"] = Alert(
                "system_fault", "CRITICAL", "Device entered FAULT state", state, "NORMAL"
            )

        if stale:
            conditions["telemetry_stale"] = Alert(
                "telemetry_stale", "CRITICAL", "Telemetry link is stale"
            )

        if data.get("CRC_VALID") is False and data.get("CRC") is not None:
            conditions["crc_invalid"] = Alert(
                "crc_invalid", "CRITICAL", "CRC validation failed"
            )

        raised = [alert for key, alert in conditions.items() if key not in self._active]
        cleared = [alert for key, alert in self._active.items() if key not in conditions]
        self._active = conditions
        return {
            "raised": raised,
            "cleared": cleared,
            "active": self.active_alerts,
        }
