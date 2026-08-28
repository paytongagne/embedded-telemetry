import tempfile
import unittest
from pathlib import Path

from ground_station.database import TelemetryDatabase


class TelemetryDatabaseTests(unittest.TestCase):
    def test_session_telemetry_and_events_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            database = TelemetryDatabase(Path(directory) / "telemetry.db")
            session_id = database.start_session("Simulator", "DEMO")

            database.log_telemetry(
                session_id,
                {
                    "SEQ": 7,
                    "TIME": 1234,
                    "TEMP": 25.5,
                    "PRESS": 980.1,
                    "HUM": 31.2,
                    "AX": 0.01,
                    "AY": -0.02,
                    "AZ": 0.99,
                    "GX": 0.1,
                    "GY": 0.2,
                    "GZ": -0.3,
                    "BME": "OK",
                    "IMU": "OK",
                    "AUX": "PRESENT",
                    "STATUS": "NORMAL",
                    "CRC_VALID": True,
                    "FW": "1.1.0",
                },
            )
            database.set_firmware_version(session_id, "1.1.0")
            database.log_event(session_id, "INFO", "TEST", "round trip")
            database.end_session(session_id)

            sessions = database.list_sessions()
            telemetry = database.load_session_telemetry(session_id)
            events = database.load_session_events(session_id)

            self.assertEqual(len(sessions), 1)
            self.assertEqual(sessions[0]["packet_count"], 1)
            self.assertEqual(sessions[0]["firmware_version"], "1.1.0")
            self.assertEqual(telemetry[0]["sequence"], 7)
            self.assertAlmostEqual(telemetry[0]["temperature_c"], 25.5)
            self.assertEqual(telemetry[0]["system_state"], "NORMAL")
            self.assertEqual(events[0]["category"], "TEST")

            database.close()


if __name__ == "__main__":
    unittest.main()
