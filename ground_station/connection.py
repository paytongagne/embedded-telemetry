from dataclasses import dataclass

from ground_station.demo_serial import DemoSerialManager
from ground_station.mqtt_manager import MqttManager
from ground_station.serial_manager import SerialManager
from ground_station.tcp_manager import TcpManager


@dataclass
class ConnectionConfig:
    mode: str = "serial"
    serial_port: str = "COM3"
    baud: int = 115200
    host: str = ""
    tcp_port: int = 9000
    mqtt_port: int = 1883
    device_id: str = "esp8285-node"
    mqtt_user: str | None = None
    mqtt_password: str | None = None


def create_manager(config: ConnectionConfig):
    mode = config.mode.strip().lower()

    if mode == "serial":
        return SerialManager(port=config.serial_port, baud=config.baud)

    if mode in {"wifi", "tcp"}:
        if not config.host.strip():
            raise ValueError("A device IP address or hostname is required for Direct WiFi.")
        return TcpManager(host=config.host.strip(), port=config.tcp_port)

    if mode == "mqtt":
        if not config.host.strip():
            raise ValueError("An MQTT broker address is required.")
        return MqttManager(
            host=config.host.strip(),
            port=config.mqtt_port,
            device_id=config.device_id.strip() or "esp8285-node",
            username=(config.mqtt_user or "").strip() or None,
            password=config.mqtt_password or None,
        )

    if mode == "demo":
        return DemoSerialManager()

    raise ValueError(f"Unsupported connection mode: {config.mode}")


def connection_metadata(manager):
    manager_name = manager.__class__.__name__

    if manager_name == "SerialManager":
        return "USB / Serial", str(getattr(manager, "port", "serial"))

    if manager_name == "TcpManager":
        return (
            "Direct WiFi",
            f"{getattr(manager, 'host', '')}:{getattr(manager, 'port', 9000)}",
        )

    if manager_name == "MqttManager":
        return (
            "MQTT",
            f"{getattr(manager, 'host', '')}:{getattr(manager, 'mqtt_port', 1883)}"
            f"/{getattr(manager, 'device_id', 'esp8285-node')}",
        )

    if manager_name == "DemoSerialManager":
        return "Simulator", "DEMO"

    return manager_name, str(getattr(manager, "port", "unknown"))
