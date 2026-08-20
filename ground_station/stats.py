import time
from collections import deque


class TelemetryStats:
    def __init__(self):
        self.total_packets = 0
        self.malformed_packets = 0
        self.lost_packets = 0

        self.last_sequence = None
        self.last_packet_time = None
        self.session_start_time = time.time()

        self.packet_rate_hz = 0.0
        self.average_packet_rate_hz = 0.0
        self._rate_samples = deque(maxlen=30)
        self.serial_reconnects = 0

        self.min_temperature = None
        self.max_temperature = None
        self.min_pressure = None
        self.max_pressure = None
        self.min_humidity = None
        self.max_humidity = None

        self.peak_acceleration = 0.0
        self.peak_gyro = 0.0

    @property
    def packet_loss_percent(self):
        expected = self.total_packets + self.lost_packets
        if expected <= 0:
            return 0.0
        return (self.lost_packets / expected) * 100.0

    @property
    def session_duration_seconds(self):
        return max(0.0, time.time() - self.session_start_time)

    def update(self, data):
        if data is None:
            self.malformed_packets += 1
            return

        self.total_packets += 1
        current_sequence = data.get("sequence")

        if self.last_sequence is not None and current_sequence is not None:
            expected = self.last_sequence + 1
            if current_sequence > expected:
                self.lost_packets += current_sequence - expected

        self.last_sequence = current_sequence

        now = time.time()
        if self.last_packet_time is not None:
            delta = now - self.last_packet_time
            if delta > 0:
                self.packet_rate_hz = 1.0 / delta
                self._rate_samples.append(self.packet_rate_hz)
                self.average_packet_rate_hz = (
                    sum(self._rate_samples) / len(self._rate_samples)
                )

        self.last_packet_time = now
        self._update_environment_stats(data)
        self._update_motion_stats(data)

    def _update_environment_stats(self, data):
        temperature = data.get("TEMP")
        pressure = data.get("PRESS")
        humidity = data.get("HUM")

        if temperature is not None:
            if self.min_temperature is None or temperature < self.min_temperature:
                self.min_temperature = temperature
            if self.max_temperature is None or temperature > self.max_temperature:
                self.max_temperature = temperature

        if pressure is not None:
            if self.min_pressure is None or pressure < self.min_pressure:
                self.min_pressure = pressure
            if self.max_pressure is None or pressure > self.max_pressure:
                self.max_pressure = pressure

        if humidity is not None:
            if self.min_humidity is None or humidity < self.min_humidity:
                self.min_humidity = humidity
            if self.max_humidity is None or humidity > self.max_humidity:
                self.max_humidity = humidity

    def _update_motion_stats(self, data):
        values = [
            data.get("AX"), data.get("AY"), data.get("AZ"),
            data.get("GX"), data.get("GY"), data.get("GZ"),
        ]

        if None in values:
            return

        ax, ay, az, gx, gy, gz = values
        acceleration_magnitude = (ax ** 2 + ay ** 2 + az ** 2) ** 0.5
        gyro_magnitude = (gx ** 2 + gy ** 2 + gz ** 2) ** 0.5

        if acceleration_magnitude > self.peak_acceleration:
            self.peak_acceleration = acceleration_magnitude
        if gyro_magnitude > self.peak_gyro:
            self.peak_gyro = gyro_magnitude

    def register_reconnect(self):
        self.serial_reconnects += 1

    def reset(self):
        self.__init__()
