import unittest

from ground_station.connection import ConnectionConfig, connection_metadata, create_manager
from ground_station.demo_serial import DemoSerialManager
from ground_station.serial_manager import SerialManager
from ground_station.tcp_manager import TcpManager


class ConnectionFactoryTests(unittest.TestCase):
    def test_serial_manager_creation(self):
        manager = create_manager(
            ConnectionConfig(mode="serial", serial_port="COM7", baud=57600)
        )
        self.assertIsInstance(manager, SerialManager)
        self.assertEqual(manager.port, "COM7")
        self.assertEqual(manager.baud, 57600)

    def test_wifi_manager_creation(self):
        manager = create_manager(
            ConnectionConfig(mode="wifi", host="192.168.1.50", tcp_port=9001)
        )
        self.assertIsInstance(manager, TcpManager)
        self.assertEqual(manager.host, "192.168.1.50")
        self.assertEqual(manager.port, 9001)

    def test_demo_manager_creation(self):
        manager = create_manager(ConnectionConfig(mode="demo"))
        self.assertIsInstance(manager, DemoSerialManager)
        self.assertEqual(connection_metadata(manager), ("Simulator", "DEMO"))

    def test_wifi_requires_host(self):
        with self.assertRaises(ValueError):
            create_manager(ConnectionConfig(mode="wifi", host=""))


if __name__ == "__main__":
    unittest.main()
