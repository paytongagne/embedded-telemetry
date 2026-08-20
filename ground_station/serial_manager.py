import queue
import threading
import time

import serial
import serial.tools.list_ports


class SerialManager:
    def __init__(
        self,
        port="COM3",
        baud=115200,
        timeout=0.1,
    ):
        self.port = port
        self.baud = baud
        self.timeout = timeout

        self.serial = None
        self.thread = None

        self.running = False
        self.connected = False
        self.auto_reconnect = True
        self.reconnect_delay = 2.0

        self.line_queue = queue.Queue()
        self.event_queue = queue.Queue()

        self.write_lock = threading.Lock()

    @staticmethod
    def available_ports():
        ports = []

        for port in serial.tools.list_ports.comports():
            ports.append(
                {
                    "device": port.device,
                    "description": port.description,
                    "hwid": port.hwid,
                }
            )

        return ports

    def _open_port(self):
        self.serial = serial.Serial(
            self.port,
            self.baud,
            timeout=self.timeout,
            write_timeout=1,
        )

        self.connected = True

        self.event_queue.put(
            ("CONNECTED", self.port)
        )

    def connect(self):
        if self.connected:
            return True

        try:
            self._open_port()
            self.running = True

            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(
                    target=self._reader_loop,
                    daemon=True,
                )
                self.thread.start()

            return True

        except (serial.SerialException, OSError) as error:
            self.connected = False
            self.serial = None

            self.event_queue.put(
                ("ERROR", str(error))
            )

            return False

    def disconnect(self):
        self.auto_reconnect = False
        self.running = False

        was_connected = self.connected
        self.connected = False

        if self.serial:
            try:
                self.serial.close()
            except (serial.SerialException, OSError):
                pass

        self.serial = None

        if was_connected:
            self.event_queue.put(
                ("DISCONNECTED", self.port)
            )

    def reconnect(self):
        self.disconnect()
        time.sleep(0.25)

        self.auto_reconnect = True
        self.running = True

        return self.connect()

    def send(self, message):
        if not self.connected or not self.serial:
            return False

        if not message.endswith("\n"):
            message += "\n"

        try:
            with self.write_lock:
                self.serial.write(
                    message.encode("utf-8")
                )
                self.serial.flush()

            return True

        except (serial.SerialException, OSError) as error:
            self.event_queue.put(
                ("ERROR", str(error))
            )

            self._connection_lost()
            return False

    def _reader_loop(self):
        while self.running:
            if not self.connected:
                if not self.auto_reconnect:
                    time.sleep(0.1)
                    continue

                time.sleep(self.reconnect_delay)

                if not self.running or self.connected:
                    continue

                try:
                    self._open_port()
                except (serial.SerialException, OSError) as error:
                    self.serial = None
                    self.connected = False
                    self.event_queue.put(
                        ("ERROR", f"Reconnect failed: {error}")
                    )

                continue

            try:
                raw = self.serial.readline()

                if not raw:
                    continue

                line = raw.decode(
                    "utf-8",
                    errors="ignore",
                ).strip()

                if line:
                    self.line_queue.put(line)

            except (serial.SerialException, OSError) as error:
                self.event_queue.put(
                    ("ERROR", str(error))
                )

                self._connection_lost()

    def _connection_lost(self):
        was_connected = self.connected
        self.connected = False

        if self.serial:
            try:
                self.serial.close()
            except Exception:
                pass

        self.serial = None

        if was_connected:
            self.event_queue.put(
                ("DISCONNECTED", self.port)
            )

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

    def set_port(self, port):
        if self.connected:
            raise RuntimeError(
                "Disconnect before changing serial port"
            )

        self.port = port

    def set_baud(self, baud):
        if self.connected:
            raise RuntimeError(
                "Disconnect before changing baud rate"
            )

        self.baud = int(baud)
