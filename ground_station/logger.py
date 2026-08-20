import csv
import json
import os
import time
from datetime import datetime


TELEMETRY_FIELDS = [
    "pc_time",
    "sequence",
    "TIME",
    "TEMP",
    "PRESS",
    "HUM",
    "AX",
    "AY",
    "AZ",
    "GX",
    "GY",
    "GZ",
    "DIST",
    "TOF_TIMEOUT",
    "I2C_ERR",
    "BME",
    "IMU",
    "AUX",
    "STATUS",
]


class TelemetryLogger:
    def __init__(self, log_directory="logs"):
        self.log_directory = log_directory

        self.telemetry_file = None
        self.telemetry_writer = None

        self.event_file = None
        self.event_writer = None

        self.session_start_time = None
        self.session_id = None

        self.telemetry_path = None
        self.event_path = None
        self.session_path = None

        self.logging_enabled = False

    def start(self):
        os.makedirs(self.log_directory, exist_ok=True)

        self.session_start_time = datetime.now()
        self.session_id = self.session_start_time.strftime(
            "%Y%m%d_%H%M%S"
        )

        self.telemetry_path = os.path.join(
            self.log_directory,
            f"telemetry_{self.session_id}.csv",
        )

        self.event_path = os.path.join(
            self.log_directory,
            f"events_{self.session_id}.csv",
        )

        self.session_path = os.path.join(
            self.log_directory,
            f"session_{self.session_id}.json",
        )

        self.telemetry_file = open(
            self.telemetry_path,
            "w",
            newline="",
            encoding="utf-8",
        )

        self.telemetry_writer = csv.DictWriter(
            self.telemetry_file,
            fieldnames=TELEMETRY_FIELDS,
            extrasaction="ignore",
        )

        self.telemetry_writer.writeheader()

        self.event_file = open(
            self.event_path,
            "w",
            newline="",
            encoding="utf-8",
        )

        self.event_writer = csv.DictWriter(
            self.event_file,
            fieldnames=[
                "pc_time",
                "level",
                "event",
                "details",
            ],
        )

        self.event_writer.writeheader()

        self.logging_enabled = True

        self.log_event(
            "INFO",
            "SESSION_START",
            "Telemetry logging started",
        )

    def log_telemetry(self, data):
        if not self.logging_enabled:
            return

        if data is None:
            return

        row = dict(data)

        row["pc_time"] = datetime.now().isoformat(
            timespec="milliseconds"
        )

        self.telemetry_writer.writerow(row)
        self.telemetry_file.flush()

    def log_event(self, level, event, details=""):
        if not self.logging_enabled:
            return

        row = {
            "pc_time": datetime.now().isoformat(
                timespec="milliseconds"
            ),
            "level": level,
            "event": event,
            "details": details,
        }

        self.event_writer.writerow(row)
        self.event_file.flush()

    def save_session_summary(self, stats, device_info=None):
        if self.session_start_time is None:
            return

        end_time = datetime.now()

        duration_seconds = (
            end_time - self.session_start_time
        ).total_seconds()

        summary = {
            "session_id": self.session_id,
            "start_time": self.session_start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration_seconds,
            "telemetry_file": self.telemetry_path,
            "event_file": self.event_path,
            "device": device_info or {},
            "statistics": {
                "total_packets": stats.total_packets,
                "malformed_packets": stats.malformed_packets,
                "lost_packets": stats.lost_packets,
                "packet_rate_hz": stats.packet_rate_hz,
                "serial_reconnects": stats.serial_reconnects,
                "min_temperature": stats.min_temperature,
                "max_temperature": stats.max_temperature,
                "min_pressure": stats.min_pressure,
                "max_pressure": stats.max_pressure,
                "min_humidity": stats.min_humidity,
                "max_humidity": stats.max_humidity,
                "peak_acceleration": stats.peak_acceleration,
                "peak_gyro": stats.peak_gyro,
            },
        }

        with open(
            self.session_path,
            "w",
            encoding="utf-8",
        ) as session_file:
            json.dump(
                summary,
                session_file,
                indent=4,
            )

    def stop(self, stats=None, device_info=None):
        if not self.logging_enabled:
            return

        self.log_event(
            "INFO",
            "SESSION_END",
            "Telemetry logging stopped",
        )

        if stats is not None:
            self.save_session_summary(
                stats,
                device_info,
            )

        if self.telemetry_file:
            self.telemetry_file.close()

        if self.event_file:
            self.event_file.close()

        self.telemetry_file = None
        self.telemetry_writer = None

        self.event_file = None
        self.event_writer = None

        self.logging_enabled = False