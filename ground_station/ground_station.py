import argparse

from ground_station.app import run
from ground_station.demo_serial import DemoSerialManager


def main():
    parser = argparse.ArgumentParser(
        description="Embedded Telemetry Ground Station"
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Run against the built-in telemetry simulator",
    )
    args = parser.parse_args()

    serial_manager = DemoSerialManager() if args.demo else None
    run(serial_manager=serial_manager)


if __name__ == "__main__":
    main()
