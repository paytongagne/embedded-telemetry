import unittest

from ground_station.demo_serial import DemoSerialManager
from ground_station.protocol import parse_response


class FaultStateTests(unittest.TestCase):
    def setUp(self):
        self.device = DemoSerialManager()
        self.device.connected = True

    def _responses(self):
        responses = []
        while True:
            line = self.device.get_line_nowait()
            if line is None:
                break
            responses.append(parse_response(line))
        return [response for response in responses if response]

    def _latest_status(self):
        statuses = [
            response
            for response in self._responses()
            if response.get("type") == "STATUS"
        ]
        self.assertTrue(statuses)
        return statuses[-1]

    def test_imu_fault_moves_to_degraded(self):
        self.device.send("CMD,INJECT_FAULT,IMU")
        status = self._latest_status()

        self.assertEqual(status["STATE"], "DEGRADED")
        self.assertEqual(status["BME"], "OK")
        self.assertEqual(status["IMU"], "FAULT")

    def test_bme_fault_moves_to_degraded(self):
        self.device.send("CMD,INJECT_FAULT,BME")
        status = self._latest_status()

        self.assertEqual(status["STATE"], "DEGRADED")
        self.assertEqual(status["BME"], "FAULT")
        self.assertEqual(status["IMU"], "OK")

    def test_two_sensor_faults_move_to_fault(self):
        self.device.send("CMD,INJECT_FAULT,IMU")
        self._responses()
        self.device.send("CMD,INJECT_FAULT,BME")
        status = self._latest_status()

        self.assertEqual(status["STATE"], "FAULT")

    def test_clear_faults_recovers_normal_state(self):
        self.device.send("CMD,INJECT_FAULT,IMU")
        self._responses()
        self.device.send("CMD,CLEAR_FAULTS")
        status = self._latest_status()

        self.assertEqual(status["STATE"], "NORMAL")
        self.assertEqual(status["BME"], "OK")
        self.assertEqual(status["IMU"], "OK")


if __name__ == "__main__":
    unittest.main()
