import unittest

from ground_station.mqtt_manager import MqttManager


class MqttManagerTests(unittest.TestCase):
    def setUp(self):
        self.manager = MqttManager(
            host="127.0.0.1",
            port=1883,
            device_id="test-node",
        )

    def test_topic_layout(self):
        self.assertEqual(
            self.manager.telemetry_topic,
            "embedded-telemetry/test-node/telemetry",
        )
        self.assertEqual(
            self.manager.command_topic,
            "embedded-telemetry/test-node/command",
        )
        self.assertEqual(
            self.manager.response_topic,
            "embedded-telemetry/test-node/response",
        )
        self.assertEqual(
            self.manager.availability_topic,
            "embedded-telemetry/test-node/availability",
        )

    def test_virtual_port_metadata(self):
        ports = self.manager.available_ports()
        self.assertEqual(len(ports), 1)
        self.assertEqual(ports[0]["device"], "MQTT:test-node")
        self.assertIn("127.0.0.1:1883", ports[0]["description"])

    def test_send_requires_connection(self):
        self.assertFalse(self.manager.send("CMD,STATUS"))


if __name__ == "__main__":
    unittest.main()
