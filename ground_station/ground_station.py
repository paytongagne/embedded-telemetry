import argparse
import atexit
import sys

from ground_station.connection import ConnectionConfig, create_manager
from ground_station.recording_manager import RecordingManager
from ground_station.selector_manager import ConnectionSelectorManager
from ground_station.v2_app import run_v2


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


def build_manager(args):
    if args.demo:
        return create_manager(ConnectionConfig(mode="demo"))

    if args.wifi:
        return create_manager(
            ConnectionConfig(
                mode="wifi",
                host=args.wifi,
                tcp_port=args.wifi_port,
            )
        )

    if args.mqtt:
        return create_manager(
            ConnectionConfig(
                mode="mqtt",
                host=args.mqtt,
                mqtt_port=args.mqtt_port,
                device_id=args.device,
                mqtt_user=args.mqtt_user,
                mqtt_password=args.mqtt_password,
            )
        )

    return ConnectionSelectorManager()


def main():
    args = parse_args()
    sys.argv = [sys.argv[0]]

    manager = RecordingManager(build_manager(args))
    atexit.register(manager.close)
    run_v2(serial_manager=manager)


if __name__ == "__main__":
    main()
