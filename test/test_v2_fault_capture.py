import json
import tempfile
import unittest
from pathlib import Path

from ground_station.fault_capture import FaultBlackBox
from ground_station.session_analysis import compare_summaries, summarize_session


class FaultBlackBoxTests(unittest.TestCase):
    def test_pre_and_post_fault_capture(self):
        with tempfile.TemporaryDirectory() as directory:
            capture = FaultBlackBox(pre_samples=3, post_samples=2, output_dir=directory)

            for seq in range(3):
                self.assertIsNone(capture.update({"SEQ": seq, "STATUS": "NORMAL"}))

            self.assertIsNone(
                capture.update({"SEQ": 3, "STATUS": "FAULT"}, metadata={"fw": "2.0"})
            )
            self.assertIsNone(capture.update({"SEQ": 4, "STATUS": "FAULT"}))
            path = capture.update({"SEQ": 5, "STATUS": "NORMAL"})

            self.assertIsNotNone(path)
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            self.assertEqual([item["SEQ"] for item in payload["pre_fault"]], [0, 1, 2])
            self.assertEqual(payload["trigger"]["SEQ"], 3)
            self.assertEqual([item["SEQ"] for item in payload["post_fault"]], [4, 5])
            self.assertEqual(payload["metadata"]["fw"], "2.0")


class SessionAnalysisTests(unittest.TestCase):
    def test_summary_and_comparison(self):
        baseline_rows = [
            {
                "device_time_ms": 0,
                "temperature_c": 20.0,
                "ax_g": 0.0,
                "ay_g": 0.0,
                "az_g": 1.0,
                "gx_dps": 0.0,
                "gy_dps": 0.0,
                "gz_dps": 5.0,
                "crc_valid": 1,
                "system_state": "NORMAL",
            },
            {
                "device_time_ms": 1000,
                "temperature_c": 22.0,
                "ax_g": 0.0,
                "ay_g": 0.0,
                "az_g": 1.0,
                "gx_dps": 0.0,
                "gy_dps": 0.0,
                "gz_dps": 5.0,
                "crc_valid": 1,
                "system_state": "NORMAL",
            },
        ]
        candidate_rows = [dict(row) for row in baseline_rows]
        candidate_rows[1]["temperature_c"] = 24.0
        candidate_rows[1]["system_state"] = "DEGRADED"

        baseline = summarize_session(baseline_rows)
        candidate = summarize_session(candidate_rows)
        comparison = compare_summaries(baseline, candidate)

        self.assertEqual(baseline["packet_count"], 2)
        self.assertAlmostEqual(baseline["duration_seconds"], 1.0)
        self.assertAlmostEqual(baseline["accel_rms_g"], 1.0)
        self.assertEqual(candidate["degraded_packets"], 1)
        self.assertAlmostEqual(comparison["temperature_max_c"]["delta"], 2.0)


if __name__ == "__main__":
    unittest.main()
