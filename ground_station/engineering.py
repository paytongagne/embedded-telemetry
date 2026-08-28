import math
from collections import deque


def _number(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def vector_magnitude(x, y, z):
    values = (_number(x), _number(y), _number(z))
    if any(value is None for value in values):
        return None
    return math.sqrt(sum(value * value for value in values))


def _rms(values):
    if not values:
        return 0.0
    return math.sqrt(sum(value * value for value in values) / len(values))


def _std(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return math.sqrt(sum((value - mean) ** 2 for value in values) / len(values))


class EngineeringMetrics:
    """Rolling engineering metrics derived from accepted telemetry packets."""

    def __init__(self, window_size=50):
        self.window_size = max(5, int(window_size))
        self.acceleration = deque(maxlen=self.window_size)
        self.gyro = deque(maxlen=self.window_size)
        self.temperature = deque(maxlen=self.window_size)
        self.last = {}

    def reset(self):
        self.acceleration.clear()
        self.gyro.clear()
        self.temperature.clear()
        self.last = {}

    def update(self, data):
        accel = vector_magnitude(data.get("AX"), data.get("AY"), data.get("AZ"))
        gyro = vector_magnitude(data.get("GX"), data.get("GY"), data.get("GZ"))
        temp = _number(data.get("TEMP"))

        if accel is not None:
            self.acceleration.append(accel)
        if gyro is not None:
            self.gyro.append(gyro)
        if temp is not None:
            self.temperature.append(temp)

        metrics = {
            "accel_magnitude_g": accel,
            "gyro_magnitude_dps": gyro,
            "accel_rms_g": _rms(self.acceleration),
            "gyro_rms_dps": _rms(self.gyro),
            "accel_std_g": _std(self.acceleration),
            "gyro_std_dps": _std(self.gyro),
            "window_samples": max(len(self.acceleration), len(self.gyro)),
        }

        if len(self.temperature) >= 2:
            metrics["temperature_delta_c"] = self.temperature[-1] - self.temperature[0]
        else:
            metrics["temperature_delta_c"] = 0.0

        self.last = metrics
        return dict(metrics)
