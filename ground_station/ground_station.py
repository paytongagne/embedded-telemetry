import sys

from ground_station.app import run
from ground_station.demo_serial import DemoSerialManager


def main():
    demo_mode = "--demo" in sys.argv

    if demo_mode:
        run(serial_manager=DemoSerialManager())
        return

    run()


if __name__ == "__main__":
    main()
