import math
from collections import deque


class FlightMotionEstimator:
    """Short-window relative motion estimator for visualization only.

    Horizontal motion is IMU-derived in the local forward/lateral frame and is
    intentionally damped to limit drift. Vertical motion uses pressure relative
    to the first valid sample. This is not a navigation solution and should not
    be used as flight-control position feedback.
    """

    GRAVITY_MPS2 = 9.80665

    def __init__(self, trail_length=120):
        self.trail_length = int(trail_length)
        self.reset()

    def reset(self):
        self.reference_pressure_hpa = None
        self.last_time_ms = None
        self.velocity_forward_mps = 0.0
        self.velocity_lateral_mps = 0.0
        self.forward_m = 0.0
        self.lateral_m = 0.0
        self.altitude_m = 0.0
        self.trail = deque(maxlen=self.trail_length)
        self.trail.append((0.0, 0.0, 0.0))

    @staticmethod
    def _float(value):
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) else None

    @staticmethod
    def _deadband(value, threshold=0.025):
        if abs(value) <= threshold:
            return 0.0
        return math.copysign(abs(value) - threshold, value)

    def _relative_altitude(self, pressure_hpa):
        pressure = self._float(pressure_hpa)
        if pressure is None or pressure <= 0.0:
            return self.altitude_m

        if self.reference_pressure_hpa is None:
            self.reference_pressure_hpa = pressure
            return 0.0

        ratio = max(0.2, min(2.0, pressure / self.reference_pressure_hpa))
        return 44330.0 * (1.0 - ratio ** 0.190294957)

    def update(self, telemetry, pitch_deg=None, roll_deg=None):
        pressure = telemetry.get("PRESS")
        self.altitude_m = self._relative_altitude(pressure)

        time_ms = self._float(telemetry.get("TIME"))
        ax = self._float(telemetry.get("AX"))
        ay = self._float(telemetry.get("AY"))
        az = self._float(telemetry.get("AZ"))
        gx = self._float(telemetry.get("GX"))
        gy = self._float(telemetry.get("GY"))
        gz = self._float(telemetry.get("GZ"))

        pitch = math.radians(float(pitch_deg or 0.0))
        roll = math.radians(float(roll_deg or 0.0))

        expected_ax = -math.sin(pitch)
        expected_ay = math.sin(roll) * math.cos(pitch)
        expected_az = math.cos(roll) * math.cos(pitch)

        dynamic_ax_g = 0.0 if ax is None else self._deadband(ax - expected_ax)
        dynamic_ay_g = 0.0 if ay is None else self._deadband(ay - expected_ay)
        dynamic_az_g = 0.0 if az is None else self._deadband(az - expected_az)

        dt = None
        if time_ms is not None and self.last_time_ms is not None:
            dt = (time_ms - self.last_time_ms) / 1000.0
        if time_ms is not None:
            self.last_time_ms = time_ms

        if dt is not None and 0.0 < dt <= 2.5 and ax is not None and ay is not None:
            forward_accel = dynamic_ax_g * self.GRAVITY_MPS2
            lateral_accel = dynamic_ay_g * self.GRAVITY_MPS2

            gyro_mag = math.sqrt(sum(value * value for value in (gx or 0.0, gy or 0.0, gz or 0.0)))
            dynamic_mag = math.sqrt(dynamic_ax_g * dynamic_ax_g + dynamic_ay_g * dynamic_ay_g)
            nearly_stationary = dynamic_mag < 0.035 and gyro_mag < 3.0

            if nearly_stationary:
                self.velocity_forward_mps *= 0.15
                self.velocity_lateral_mps *= 0.15
            else:
                damping = math.exp(-dt / 1.1)
                self.velocity_forward_mps = (
                    self.velocity_forward_mps * damping + forward_accel * dt
                )
                self.velocity_lateral_mps = (
                    self.velocity_lateral_mps * damping + lateral_accel * dt
                )

            self.forward_m += self.velocity_forward_mps * dt
            self.lateral_m += self.velocity_lateral_mps * dt

            # Keep the visualization bounded and slowly forget old integration drift.
            position_decay = math.exp(-dt / 25.0)
            self.forward_m *= position_decay
            self.lateral_m *= position_decay
            self.forward_m = max(-5.0, min(5.0, self.forward_m))
            self.lateral_m = max(-5.0, min(5.0, self.lateral_m))

        self.trail.append((self.forward_m, self.lateral_m, self.altitude_m))

        return {
            "forward_m": self.forward_m,
            "lateral_m": self.lateral_m,
            "altitude_m": self.altitude_m,
            "velocity_forward_mps": self.velocity_forward_mps,
            "velocity_lateral_mps": self.velocity_lateral_mps,
            "dynamic_ax_g": dynamic_ax_g,
            "dynamic_ay_g": dynamic_ay_g,
            "dynamic_az_g": dynamic_az_g,
            "pressure_hpa": self._float(pressure),
            "trail": list(self.trail),
            "xy_source": "IMU short-window estimate",
            "z_source": "barometric relative altitude" if self.reference_pressure_hpa else "unavailable",
        }
