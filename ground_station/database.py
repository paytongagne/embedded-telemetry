import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path


class TelemetryDatabase:
    def __init__(self, path="data/telemetry.db"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._connection = sqlite3.connect(self.path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._connection.execute("PRAGMA journal_mode = WAL")
        self._create_schema()

    @staticmethod
    def _utc_now():
        return datetime.now(timezone.utc).isoformat()

    def _create_schema(self):
        with self._connection:
            self._connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at_utc TEXT NOT NULL,
                    ended_at_utc TEXT,
                    transport TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    firmware_version TEXT,
                    packet_count INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS telemetry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER NOT NULL,
                    recorded_at_utc TEXT NOT NULL,
                    sequence INTEGER,
                    device_time_ms INTEGER,
                    temperature_c REAL,
                    pressure_hpa REAL,
                    humidity_percent REAL,
                    ax_g REAL,
                    ay_g REAL,
                    az_g REAL,
                    gx_dps REAL,
                    gy_dps REAL,
                    gz_dps REAL,
                    bme_state TEXT,
                    imu_state TEXT,
                    aux_state TEXT,
                    system_state TEXT,
                    crc_valid INTEGER,
                    payload_json TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_telemetry_session_time
                ON telemetry(session_id, recorded_at_utc);

                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id INTEGER,
                    recorded_at_utc TEXT NOT NULL,
                    level TEXT NOT NULL,
                    category TEXT NOT NULL,
                    message TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_events_session_time
                ON events(session_id, recorded_at_utc);
                """
            )

    def start_session(self, transport, endpoint):
        with self._lock, self._connection:
            cursor = self._connection.execute(
                """
                INSERT INTO sessions(started_at_utc, transport, endpoint)
                VALUES (?, ?, ?)
                """,
                (self._utc_now(), str(transport), str(endpoint)),
            )
            return cursor.lastrowid

    def end_session(self, session_id):
        if session_id is None:
            return
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE sessions SET ended_at_utc = ? WHERE id = ? AND ended_at_utc IS NULL",
                (self._utc_now(), session_id),
            )

    def set_firmware_version(self, session_id, firmware_version):
        if session_id is None or firmware_version in (None, ""):
            return
        with self._lock, self._connection:
            self._connection.execute(
                "UPDATE sessions SET firmware_version = ? WHERE id = ?",
                (str(firmware_version), session_id),
            )

    def log_telemetry(self, session_id, data):
        if session_id is None:
            return

        payload = json.dumps(data, sort_keys=True, default=str)
        values = (
            session_id,
            self._utc_now(),
            self._to_int(data.get("SEQ")),
            self._to_int(data.get("TIME")),
            self._to_float(data.get("TEMP")),
            self._to_float(data.get("PRESS")),
            self._to_float(data.get("HUM")),
            self._to_float(data.get("AX")),
            self._to_float(data.get("AY")),
            self._to_float(data.get("AZ")),
            self._to_float(data.get("GX")),
            self._to_float(data.get("GY")),
            self._to_float(data.get("GZ")),
            self._to_text(data.get("BME")),
            self._to_text(data.get("IMU")),
            self._to_text(data.get("AUX")),
            self._to_text(data.get("STATUS", data.get("STATE"))),
            1 if data.get("CRC_VALID") else 0,
            payload,
        )

        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO telemetry(
                    session_id, recorded_at_utc, sequence, device_time_ms,
                    temperature_c, pressure_hpa, humidity_percent,
                    ax_g, ay_g, az_g, gx_dps, gy_dps, gz_dps,
                    bme_state, imu_state, aux_state, system_state, crc_valid,
                    payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                values,
            )
            self._connection.execute(
                "UPDATE sessions SET packet_count = packet_count + 1 WHERE id = ?",
                (session_id,),
            )

    def log_event(self, session_id, level, category, message):
        with self._lock, self._connection:
            self._connection.execute(
                """
                INSERT INTO events(session_id, recorded_at_utc, level, category, message)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    self._utc_now(),
                    str(level),
                    str(category),
                    str(message),
                ),
            )

    def list_sessions(self, limit=100):
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT id, started_at_utc, ended_at_utc, transport, endpoint,
                       firmware_version, packet_count
                FROM sessions
                ORDER BY id DESC
                LIMIT ?
                """,
                (int(limit),),
            ).fetchall()
        return [dict(row) for row in rows]

    def load_session_telemetry(self, session_id):
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM telemetry
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def load_session_events(self, session_id):
        with self._lock:
            rows = self._connection.execute(
                """
                SELECT * FROM events
                WHERE session_id = ?
                ORDER BY id ASC
                """,
                (session_id,),
            ).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        with self._lock:
            self._connection.close()

    @staticmethod
    def _to_float(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_int(value):
        if value in (None, ""):
            return None
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _to_text(value):
        return None if value in (None, "") else str(value)
