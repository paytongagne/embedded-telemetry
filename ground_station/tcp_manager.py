import queue
import socket
import threading
import time


class TcpManager:
    def __init__(self, host, port=9000, timeout=0.25):
        self.host = host
        self.port = int(port)
        self.timeout = timeout
        self.socket = None
        self.thread = None
        self.running = False
        self.connected = False
        self.auto_reconnect = True
        self.reconnect_delay = 2.0
        self.line_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self.write_lock = threading.Lock()
        self._buffer = b""

    def available_ports(self):
        return [
            {
                "device": self.host,
                "description": f"Direct WiFi TCP :{self.port}",
                "hwid": "TCP",
            }
        ]

    def set_port(self, host):
        if self.connected:
            raise RuntimeError("Disconnect before changing WiFi host")
        self.host = host

    def set_baud(self, baud):
        return None

    def _open(self):
        sock = socket.create_connection((self.host, self.port), timeout=3.0)
        sock.settimeout(self.timeout)
        self.socket = sock
        self.connected = True
        self._buffer = b""
        self.event_queue.put(("CONNECTED", f"{self.host}:{self.port}"))

    def connect(self):
        if self.connected:
            return True

        try:
            self._open()
            self.running = True
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._reader_loop, daemon=True)
                self.thread.start()
            return True
        except OSError as error:
            self.connected = False
            self.socket = None
            self.event_queue.put(("ERROR", str(error)))
            return False

    def disconnect(self):
        self.auto_reconnect = False
        self.running = False
        was_connected = self.connected
        self.connected = False

        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None

        if was_connected:
            self.event_queue.put(("DISCONNECTED", f"{self.host}:{self.port}"))

    def reconnect(self):
        self.disconnect()
        time.sleep(0.25)
        self.auto_reconnect = True
        self.running = True
        return self.connect()

    def send(self, message):
        if not self.connected or not self.socket:
            return False

        if not message.endswith("\n"):
            message += "\n"

        try:
            with self.write_lock:
                self.socket.sendall(message.encode("utf-8"))
            return True
        except OSError as error:
            self.event_queue.put(("ERROR", str(error)))
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
                    self._open()
                except OSError as error:
                    self.socket = None
                    self.connected = False
                    self.event_queue.put(("ERROR", f"Reconnect failed: {error}"))
                continue

            try:
                data = self.socket.recv(2048)
                if not data:
                    self._connection_lost()
                    continue

                self._buffer += data
                while b"\n" in self._buffer:
                    raw, self._buffer = self._buffer.split(b"\n", 1)
                    line = raw.decode("utf-8", errors="ignore").strip()
                    if line:
                        self.line_queue.put(line)
            except socket.timeout:
                continue
            except OSError as error:
                self.event_queue.put(("ERROR", str(error)))
                self._connection_lost()

    def _connection_lost(self):
        was_connected = self.connected
        self.connected = False
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
        self.socket = None
        if was_connected:
            self.event_queue.put(("DISCONNECTED", f"{self.host}:{self.port}"))

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
