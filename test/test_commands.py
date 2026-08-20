import unittest

from ground_station.demo_serial import DemoSerialManager
from ground_station.protocol import parse_response


class CommandIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.device = DemoSerialManager()
        self.device.connected = True

    def _drain(self):
        lines = []
        while True:
            line = self.device.get_line_nowait()
            if line is None:
                break
            lines.append(line)
        return lines

    def test_status_command_returns_ack_and_status(self):
        self.assertTrue(self.device.send("CMD,STATUS"))
        lines = self._drain()

        self.assertIn("ACK,STATUS", lines)
        statuses = [parse_response(line) for line in lines if line.startswith("STATUS,")]
        self.assertEqual(statuses[0]["STATE"], "NORMAL")

    def test_pause_and_resume(self):
        self.device.send("CMD,PAUSE")
        self.assertTrue(self.device.paused)
        self._drain()

        self.device.send("CMD,RESUME")
        self.assertFalse(self.device.paused)
        self.assertIn("ACK,RESUME", self._drain())

    def test_set_rate(self):
        self.device.send("CMD,SET_RATE,500")
        self.assertEqual(self.device.rate_ms, 500)
        self.assertIn("ACK,SET_RATE,500", self._drain())

    def test_out_of_range_rate_is_rejected(self):
        self.device.send("CMD,SET_RATE,50")
        lines = self._drain()
        self.assertTrue(any(line.startswith("ERR,RATE_RANGE") for line in lines))
        self.assertEqual(self.device.rate_ms, 1000)

    def test_missing_rate_is_rejected(self):
        self.device.send("CMD,SET_RATE")
        self.assertIn("ERR,MISSING_VALUE,SET_RATE", self._drain())

    def test_bad_fault_target_is_rejected(self):
        self.device.send("CMD,INJECT_FAULT,AUX")
        self.assertIn("ERR,BAD_TARGET,AUX", self._drain())

    def test_unknown_command_is_rejected(self):
        self.device.send("CMD,LAUNCH")
        self.assertIn("ERR,UNKNOWN_COMMAND,LAUNCH", self._drain())

    def test_command_requires_connection(self):
        self.device.connected = False
        self.assertFalse(self.device.send("CMD,STATUS"))


if __name__ == "__main__":
    unittest.main()
