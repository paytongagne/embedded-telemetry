import unittest

from ground_station.alerts import AlertEngine
from ground_station.engineering import EngineeringMetrics, vector_magnitude
from ground_station.validation import FaultValidationEngine


class EngineeringMetricTests(unittest.TestCase):
    def test_vector_magnitude(self):
        self.assertAlmostEqual(vector_magnitude(3, 4, 0), 5.0)

    def test_rolling_metrics(self):
        metrics = EngineeringMetrics(window_size=5)
        result = None
        for _ in range(5):
            result = metrics.update(
                {
                    "AX": 0.0,
                    "AY": 0.0,
                    "AZ": 1.0,
                    "GX": 3.0,
                    "GY": 4.0,
                    "GZ": 0.0,
                    "TEMP": 25.0,
                }
            )
        self.assertAlmostEqual(result["accel_magnitude_g"], 1.0)
        self.assertAlmostEqual(result["accel_rms_g"], 1.0)
        self.assertAlmostEqual(result["gyro_magnitude_dps"], 5.0)
        self.assertAlmostEqual(result["gyro_rms_dps"], 5.0)
        self.assertEqual(result["window_samples"], 5)


class AlertEngineTests(unittest.TestCase):
    def test_alert_is_edge_triggered_and_clears(self):
        engine = AlertEngine({"temperature_high_c": 30.0})
        metrics = {"accel_rms_g": 1.0, "gyro_rms_dps": 1.0}

        first = engine.evaluate({"TEMP": 31.0, "HUM": 50.0}, metrics)
        second = engine.evaluate({"TEMP": 31.0, "HUM": 50.0}, metrics)
        cleared = engine.evaluate({"TEMP": 29.0, "HUM": 50.0}, metrics)

        self.assertEqual([alert.key for alert in first["raised"]], ["temperature_high"])
        self.assertEqual(second["raised"], [])
        self.assertEqual([alert.key for alert in cleared["cleared"]], ["temperature_high"])

    def test_fault_state_is_critical(self):
        engine = AlertEngine()
        result = engine.evaluate(
            {"STATUS": "FAULT"},
            {"accel_rms_g": 0.0, "gyro_rms_dps": 0.0},
        )
        self.assertEqual(result["raised"][0].severity, "CRITICAL")


class ValidationEngineTests(unittest.TestCase):
    def test_full_fault_sequence_passes(self):
        engine = FaultValidationEngine()
        engine.start(now=0.0)

        states = ["NORMAL", "DEGRADED", "NORMAL", "DEGRADED", "FAULT", "NORMAL"]
        expected_actions = [
            None,
            "CMD,INJECT_FAULT,IMU",
            "CMD,CLEAR_FAULTS",
            "CMD,INJECT_FAULT,BME",
            "CMD,INJECT_FAULT,IMU",
            "CMD,CLEAR_FAULTS",
        ]

        self.assertEqual(engine.next_action(), expected_actions[0])
        for index, state in enumerate(states):
            engine.tick(state, connected=True, now=float(index + 1))
            if index + 1 < len(expected_actions):
                self.assertEqual(engine.next_action(), expected_actions[index + 1])

        self.assertTrue(engine.finished)
        self.assertTrue(engine.passed)
        self.assertTrue(all(result.status == "PASS" for result in engine.results))

    def test_timeout_fails_validation(self):
        engine = FaultValidationEngine()
        engine.start(now=0.0)
        engine.tick("UNKNOWN", connected=True, now=6.0)
        self.assertTrue(engine.finished)
        self.assertFalse(engine.passed)
        self.assertEqual(engine.results[0].status, "FAIL")


if __name__ == "__main__":
    unittest.main()
