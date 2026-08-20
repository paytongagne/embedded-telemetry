import sys

from ground_station.app import run


def main():
    demo_mode = "--demo" in sys.argv
    run(demo_mode=demo_mode)


if __name__ == "__main__":
    main()
