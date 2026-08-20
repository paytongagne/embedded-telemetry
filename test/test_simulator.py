import unittest

from ground_station.demo_serial import DemoSerialManager
from ground_station.parser import parse_telemetry


class SimulatorTests(unittest.TestCase):
    def setUp(self):
        self.device = DemoSerialManager()

    def test_generated_packet_has_valid_crc(self):
        packet = self.device._build_packet()
        data = parse_telemetry(packet)

        self.assertIsNotNone(data)
        self.assertTrue(data["CRC_VALID"])
        self.assertEqual(data["STATUS"], "NORMAL")

    def test_imu_fault_omits_motion_fields(self):
        self.device.imu_fault = True
        data = parse_telemetry(self.device._build_packet())

        self.assertEqual(data["IMU"], "FAULT")
        self.assertEqual(data["STATUS"], "DEGRADED")
        self.assertNotIn("AX", data)
        self.assertNotIn("GX", data)

    def test_bme_fault_omits_environment_fields(self):
        self.device.bme_fault = True
        data = parse_telemetry(self.device._build_packet())

        self.assertEqual(data["BME"], "FAULT")
        self.assertEqual(data["STATUS"], "DEGRADED")
        self.assertNotIn("TEMP", data)
        self.assertNotIn("PRESS", data)
        self.assertNotIn("HUM", data)


if __name__ == "__main__":
    unittest.main()
