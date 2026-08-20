import math
import queue
import threading
import time

from ground_station.parser import crc16_ccitt


class DemoSerialManager:
    def __init__(self, port="DEMO", baud=115200, timeout=0.1):
        self.port = port
        self.baud = baud
        self.timeout = timeout
        self.connected = False
        self.running = False
        self.auto_reconnect = False
        self.line_queue = queue.Queue()
        self.event_queue = queue.Queue()
        self.thread = None
        self.sequence = 0
        self.rate_ms = 1000
        self.paused = False
        self.imu_fault = False
        self.bme_fault = False
        self.start_time = time.monotonic()

    @staticmethod
    def available_ports():
        return [
            {
                "device": "DEMO",
                "description": "Built-in telemetry simulator",
                "hwid": "DEMO",
            }
        ]

    def set_port(self, port):
        self.port = port

    def set_baud(self, baud):
        self.baud = int(baud)

    def connect(self):
        if self.connected:
            return True

        self.connected = True
        self.running = True
        self.start_time = time.monotonic()
        self.event_queue.put(("CONNECTED", self.port))

        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()
        return True

    def disconnect(self):
        was_connected = self.connected
        self.connected = False
        self.running = False

        if was_connected:
            self.event_queue.put(("DISCONNECTED", self.port))

    def send(self, message):
        if not self.connected:
            return False

        command = message.strip()
        parts = command.split(",")

        if len(parts) < 2 or parts[0] != "CMD":
            self.line_queue.put("ERR,BAD_FORMAT")
            return True

        name = parts[1].upper()
        value = parts[2].upper() if len(parts) > 2 else None

        if name == "STATUS":
            self.line_queue.put("ACK,STATUS")
            self._queue_status()
        elif name == "PAUSE":
            self.paused = True
            self.line_queue.put("ACK,PAUSE")
            self._queue_status()
        elif name == "RESUME":
            self.paused = False
            self.line_queue.put("ACK,RESUME")
            self._queue_status()
        elif name == "SET_RATE" and value is not None:
            try:
                requested = int(value)
            except ValueError:
                self.line_queue.put("ERR,RATE_RANGE,100-10000")
                return True

            if not 100 <= requested <= 10000:
                self.line_queue.put("ERR,RATE_RANGE,100-10000")
            else:
                self.rate_ms = requested
                self.line_queue.put(f"ACK,SET_RATE,{requested}")
                self._queue_status()
        elif name == "INJECT_FAULT" and value in {"IMU", "BME"}:
            if value == "IMU":
                self.imu_fault = True
            else:
                self.bme_fault = True
            self.line_queue.put(f"ACK,INJECT_FAULT,{value}")
            self._queue_status()
        elif name == "CLEAR_FAULTS":
            self.imu_fault = False
            self.bme_fault = False
            self.line_queue.put("ACK,CLEAR_FAULTS")
            self._queue_status()
        elif name == "RESET":
            self.sequence = 0
            self.start_time = time.monotonic()
            self.line_queue.put("ACK,RESET")
        else:
            self.line_queue.put(f"ERR,UNKNOWN_COMMAND,{name}")

        return True

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

    def _state(self):
        if not self.bme_fault and not self.imu_fault:
            return "NORMAL"
        if self.bme_fault and self.imu_fault:
            return "FAULT"
        return "DEGRADED"

    def _queue_status(self):
        self.line_queue.put(
            "STATUS,"
            f"STATE={self._state()},"
            f"BME={'FAULT' if self.bme_fault else 'OK'},"
            f"IMU={'FAULT' if self.imu_fault else 'OK'},"
            "AUX=PRESENT,"
            f"PAUSED={1 if self.paused else 0},"
            f"RATE_MS={self.rate_ms},"
            "I2C_ERR=0,RECOVERY=0,RECOVERY_ATTEMPTS=0,"
            "BME_FAIL=0,IMU_FAIL=0,FW=DEMO"
        )

    def _build_packet(self):
        self.sequence += 1
        elapsed = time.monotonic() - self.start_time
        millis = int(elapsed * 1000)

        packet = f"TEL,{self.sequence},TIME={millis}"

        if not self.bme_fault:
            temperature = 24.0 + math.sin(elapsed / 8.0) * 1.2
            pressure = 980.0 + math.sin(elapsed / 11.0) * 0.8
            humidity = 35.0 + math.sin(elapsed / 6.0) * 4.0
            packet += (
                f",TEMP={temperature:.2f},PRESS={pressure:.2f},HUM={humidity:.2f}"
            )

        if not self.imu_fault:
            ax = math.sin(elapsed / 4.0) * 0.08
            ay = math.sin(elapsed / 5.0) * 0.05
            az = math.sqrt(max(0.0, 1.0 - ax * ax - ay * ay))
            gx = math.cos(elapsed / 3.0) * 4.0
            gy = math.sin(elapsed / 3.5) * 3.0
            gz = math.sin(elapsed / 5.5) * 2.0
            packet += (
                f",AX={ax:.3f},AY={ay:.3f},AZ={az:.3f},"
                f"GX={gx:.2f},GY={gy:.2f},GZ={gz:.2f}"
            )

        packet += (
            f",BME={'FAULT' if self.bme_fault else 'OK'},"
            f"IMU={'FAULT' if self.imu_fault else 'OK'},"
            "AUX=PRESENT,I2C_ERR=0,RECOVERY=0,BME_FAIL=0,IMU_FAIL=0,"
            f"STATUS={self._state()}"
        )

        crc = crc16_ccitt(packet)
        return f"{packet},CRC={crc:04X}"

    def _loop(self):
        next_packet = time.monotonic()

        while self.running:
            now = time.monotonic()

            if not self.paused and now >= next_packet:
                self.line_queue.put(self._build_packet())
                next_packet = now + self.rate_ms / 1000.0

            time.sleep(0.01)
