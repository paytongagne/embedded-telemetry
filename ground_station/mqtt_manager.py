import queue
import threading
import time

import paho.mqtt.client as mqtt


class MqttManager:
    def __init__(
        self,
        host,
        port=1883,
        device_id="esp8285-node",
        username=None,
        password=None,
    ):
        self.host = host
        self.mqtt_port = int(port)
        self.device_id = device_id
        self.username = username or None
        self.password = password or None

        self.port = f"MQTT:{device_id}"
        self.baud = 0
        self.connected = False
        self.auto_reconnect = True

        self.line_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self._connect_event = threading.Event()
        self._client = self._make_client()

        if self.username:
            self._client.username_pw_set(self.username, self.password)

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message

    def _make_client(self):
        client_id = f"ground-station-{self.device_id}-{int(time.time())}"
        try:
            return mqtt.Client(
                mqtt.CallbackAPIVersion.VERSION1,
                client_id=client_id,
                clean_session=True,
            )
        except AttributeError:
            return mqtt.Client(client_id=client_id, clean_session=True)

    @property
    def telemetry_topic(self):
        return f"embedded-telemetry/{self.device_id}/telemetry"

    @property
    def command_topic(self):
        return f"embedded-telemetry/{self.device_id}/command"

    @property
    def response_topic(self):
        return f"embedded-telemetry/{self.device_id}/response"

    @property
    def availability_topic(self):
        return f"embedded-telemetry/{self.device_id}/availability"

    def available_ports(self):
        return [
            {
                "device": self.port,
                "description": f"MQTT {self.host}:{self.mqtt_port}",
                "hwid": self.device_id,
            }
        ]

    def connect(self):
        if self.connected:
            return True

        self._connect_event.clear()
        try:
            self._client.connect(self.host, self.mqtt_port, keepalive=20)
            self._client.loop_start()
            self._connect_event.wait(timeout=3.0)
            return self.connected
        except Exception as error:
            self.event_queue.put(("ERROR", f"MQTT connect failed: {error}"))
            return False

    def disconnect(self):
        was_connected = self.connected
        self.auto_reconnect = False
        try:
            self._client.disconnect()
        except Exception:
            pass
        try:
            self._client.loop_stop()
        except Exception:
            pass
        self.connected = False
        if was_connected:
            self.event_queue.put(("DISCONNECTED", self.port))

    def reconnect(self):
        self.auto_reconnect = True
        try:
            self._client.reconnect()
            return True
        except Exception as error:
            self.event_queue.put(("ERROR", f"MQTT reconnect failed: {error}"))
            return False

    def send(self, message):
        if not self.connected:
            return False

        payload = message.rstrip("\r\n")
        result = self._client.publish(self.command_topic, payload, qos=1)
        return result.rc == mqtt.MQTT_ERR_SUCCESS

    def set_port(self, port):
        if self.connected:
            raise RuntimeError("Disconnect before changing transport")
        self.port = port

    def set_baud(self, baud):
        self.baud = int(baud)

    def get_line_nowait(self):
        try:
            return self.line_queue.get_nowait()
        except queue.Empty:
            return None

    def get_event_nowait(self):
        try:
            return self.event_queue.get_nowait()
        except queue.Empty:
            return None

    def _on_connect(self, client, userdata, flags, rc):
        if rc != 0:
            self.event_queue.put(("ERROR", f"MQTT broker rejected connection: {rc}"))
            self._connect_event.set()
            return

        self.connected = True
        self.auto_reconnect = True
        client.subscribe(self.telemetry_topic, qos=1)
        client.subscribe(self.response_topic, qos=1)
        client.subscribe(self.availability_topic, qos=1)
        self.event_queue.put(("CONNECTED", self.port))
        self._connect_event.set()

    def _on_disconnect(self, client, userdata, rc):
        was_connected = self.connected
        self.connected = False
        if was_connected:
            self.event_queue.put(("DISCONNECTED", self.port))
        if rc != 0 and self.auto_reconnect:
            self.event_queue.put(("ERROR", f"MQTT connection lost: {rc}"))

    def _on_message(self, client, userdata, message):
        text = message.payload.decode("utf-8", errors="replace").strip()
        if not text:
            return

        if message.topic == self.availability_topic:
            self.event_queue.put(("INFO", f"MQTT device {text}"))
            return

        self.line_queue.put(text)
