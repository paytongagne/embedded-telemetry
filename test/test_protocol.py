import unittest

from ground_station.protocol import (
    build_command,
    command_clear_faults,
    command_inject_fault,
    command_pause,
    command_reset,
    command_resume,
    command_set_rate,
    command_status,
    parse_response,
)


class ProtocolTests(unittest.TestCase):
    def test_command_builders(self):
        self.assertEqual(command_status(), "CMD,STATUS")
        self.assertEqual(command_pause(), "CMD,PAUSE")
        self.assertEqual(command_resume(), "CMD,RESUME")
        self.assertEqual(command_reset(), "CMD,RESET")
        self.assertEqual(command_clear_faults(), "CMD,CLEAR_FAULTS")
        self.assertEqual(command_set_rate(500), "CMD,SET_RATE,500")
        self.assertEqual(command_inject_fault("imu"), "CMD,INJECT_FAULT,IMU")

    def test_invalid_command_rejected(self):
        with self.assertRaises(ValueError):
            build_command("LAUNCH")

    def test_rate_bounds(self):
        self.assertEqual(command_set_rate(100), "CMD,SET_RATE,100")
        self.assertEqual(command_set_rate(10000), "CMD,SET_RATE,10000")

        with self.assertRaises(ValueError):
            command_set_rate(99)

        with self.assertRaises(ValueError):
            command_set_rate(10001)

    def test_fault_target_validation(self):
        self.assertEqual(command_inject_fault("BME"), "CMD,INJECT_FAULT,BME")

        with self.assertRaises(ValueError):
            command_inject_fault("AUX")

    def test_parse_ack(self):
        response = parse_response("ACK,SET_RATE,500")

        self.assertEqual(response["type"], "ACK")
        self.assertEqual(response["command"], "SET_RATE")
        self.assertEqual(response["value"], "500")

    def test_parse_error(self):
        response = parse_response("ERR,RATE_RANGE,100-10000")

        self.assertEqual(response["type"], "ERR")
        self.assertEqual(response["error"], "RATE_RANGE")
        self.assertEqual(response["details"], "100-10000")

    def test_parse_status(self):
        response = parse_response(
            "STATUS,STATE=NORMAL,BME=OK,IMU=OK,AUX=PRESENT,PAUSED=0,"
            "RATE_MS=1000,I2C_ERR=0,RECOVERY=0,RECOVERY_ATTEMPTS=0,"
            "BME_FAIL=0,IMU_FAIL=0,FW=0.6.0"
        )

        self.assertEqual(response["type"], "STATUS")
        self.assertEqual(response["STATE"], "NORMAL")
        self.assertEqual(response["BME"], "OK")
        self.assertEqual(response["IMU"], "OK")
        self.assertEqual(response["AUX"], "PRESENT")
        self.assertEqual(response["RECOVERY_ATTEMPTS"], "0")
        self.assertEqual(response["FW"], "0.6.0")


if __name__ == "__main__":
    unittest.main()
