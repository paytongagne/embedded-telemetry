import unittest

from ground_station.flight_dynamics import FlightMotionEstimator


class FlightMotionEstimatorTests(unittest.TestCase):
    def test_stationary_level_device_does_not_walk_away(self):
        estimator = FlightMotionEstimator()
        for index in range(8):
            result = estimator.update(
                {
                    "TIME": index * 100,
                    "PRESS": 1000.0,
                    "AX": 0.0,
                    "AY": 0.0,
                    "AZ": 1.0,
                    "GX": 0.0,
                    "GY": 0.0,
                    "GZ": 0.0,
                },
                pitch_deg=0.0,
                roll_deg=0.0,
            )

        self.assertAlmostEqual(result["forward_m"], 0.0, places=4)
        self.assertAlmostEqual(result["lateral_m"], 0.0, places=4)
        self.assertAlmostEqual(result["altitude_m"], 0.0, places=4)

    def test_forward_acceleration_produces_forward_relative_motion(self):
        estimator = FlightMotionEstimator()
        estimator.update(
            {"TIME": 0, "PRESS": 1000.0, "AX": 0.0, "AY": 0.0, "AZ": 1.0},
            pitch_deg=0.0,
            roll_deg=0.0,
        )
        result = None
        for index in range(1, 8):
            result = estimator.update(
                {
                    "TIME": index * 100,
                    "PRESS": 1000.0,
                    "AX": 0.20,
                    "AY": 0.0,
                    "AZ": 1.0,
                    "GX": 0.0,
                    "GY": 0.0,
                    "GZ": 0.0,
                },
                pitch_deg=0.0,
                roll_deg=0.0,
            )

        self.assertIsNotNone(result)
        self.assertGreater(result["forward_m"], 0.0)
        self.assertGreater(result["velocity_forward_mps"], 0.0)

    def test_lower_pressure_increases_relative_altitude(self):
        estimator = FlightMotionEstimator()
        estimator.update({"TIME": 0, "PRESS": 1000.0})
        result = estimator.update({"TIME": 100, "PRESS": 990.0})
        self.assertGreater(result["altitude_m"], 0.0)

    def test_reset_zeroes_motion_and_references(self):
        estimator = FlightMotionEstimator()
        estimator.update({"TIME": 0, "PRESS": 1000.0, "AX": 0.0, "AY": 0.0, "AZ": 1.0})
        estimator.update({"TIME": 100, "PRESS": 995.0, "AX": 0.3, "AY": 0.0, "AZ": 1.0})
        estimator.reset()

        self.assertEqual(estimator.forward_m, 0.0)
        self.assertEqual(estimator.lateral_m, 0.0)
        self.assertEqual(estimator.altitude_m, 0.0)
        self.assertIsNone(estimator.reference_pressure_hpa)
        self.assertEqual(list(estimator.trail), [(0.0, 0.0, 0.0)])


if __name__ == "__main__":
    unittest.main()
