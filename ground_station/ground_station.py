import argparse
import sys

from ground_station.app import run
from ground_station.demo_serial import DemoSerialManager
from ground_station.mqtt_manager import MqttManager
from ground_station.tcp_manager import TcpManager


def parse_args():
    parser = argparse.ArgumentParser(description="Embedded Telemetry Ground Station")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--demo", action="store_true", help="Use the hardware-free simulator")
    mode.add_argument("--wifi", metavar="HOST", help="Connect directly to the device over WiFi")
    mode.add_argument("--mqtt", metavar="HOST", help="Connect through an MQTT broker")
    parser.add_argument("--wifi-port", type=int, default=9000)
    parser.add_argument("--mqtt-port", type=int, default=1883)
    parser.add_argument("--device", default="esp8285-node")
    parser.add_argument("--mqtt-user")
    parser.add_argument("--mqtt-password")
    return parser.parse_args()


def main():
    args = parse_args()
    sys.argv = [sys.argv[0]]

    if args.demo:
        run(serial_manager=DemoSerialManager())
        return

    if args.wifi:
        run(serial_manager=TcpManager(host=args.wifi, port=args.wifi_port))
        return

    if args.mqtt:
        run(
            serial_manager=MqttManager(
                host=args.mqtt,
                port=args.mqtt_port,
                device_id=args.device,
                username=args.mqtt_user,
                password=args.mqtt_password,
            )
        )
        return

    run()


if __name__ == "__main__":
    main()
