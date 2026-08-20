import math
import sys
import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication, QComboBox, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
)

from ground_station.logger import TelemetryLogger
from ground_station.parser import parse_telemetry
from ground_station.protocol import (
    command_clear_faults, command_inject_fault, command_pause, command_reset,
    command_resume, command_set_rate, command_status, parse_response,
)
from ground_station.serial_manager import SerialManager
from ground_station.stats import TelemetryStats

MAX_POINTS = 120
STALE_TIMEOUT_SECONDS = 3.0


class GroundStationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Embedded Telemetry Ground Station")
        self.resize(1500, 950)

        self.stats = TelemetryStats()
        self.logger = TelemetryLogger()
        self.latest_data = {}
        self.last_packet_wall_time = None
        self.stale_reported = False

        self.time_history = deque(maxlen=MAX_POINTS)
        self.temp_history = deque(maxlen=MAX_POINTS)
        self.press_history = deque(maxlen=MAX_POINTS)
        self.hum_history = deque(maxlen=MAX_POINTS)
        self.ax_history = deque(maxlen=MAX_POINTS)
        self.ay_history = deque(maxlen=MAX_POINTS)
        self.az_history = deque(maxlen=MAX_POINTS)
        self.gx_history = deque(maxlen=MAX_POINTS)
        self.gy_history = deque(maxlen=MAX_POINTS)
        self.gz_history = deque(maxlen=MAX_POINTS)

        self.serial_manager = SerialManager(port="COM3", baud=115200)

        self.build_ui()

        self.gui_timer = QTimer(self)
        self.gui_timer.timeout.connect(self.process_serial)
        self.gui_timer.timeout.connect(self.refresh_gui)
        self.gui_timer.start(100)

        self.refresh_ports()

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        main_layout.addLayout(self.build_connection_bar())
        main_layout.addLayout(self.build_status_cards())
        main_layout.addLayout(self.build_health_bar())
        main_layout.addLayout(self.build_graph_section())

        lower_layout = QHBoxLayout()
        lower_layout.addWidget(self.build_diagnostics_panel(), 1)
        lower_layout.addWidget(self.build_event_panel(), 2)
        main_layout.addLayout(lower_layout)
        main_layout.addLayout(self.build_command_bar())

    def build_connection_bar(self):
        layout = QHBoxLayout()

        title = QLabel("EMBEDDED TELEMETRY GROUND STATION")
        title.setStyleSheet("font-size: 20px; font-weight: bold;")

        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.refresh_ports)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)

        self.connection_label = QLabel("DISCONNECTED")
        self.connection_label.setAlignment(Qt.AlignCenter)

        self.system_status_label = QLabel("UNKNOWN")
        self.system_status_label.setAlignment(Qt.AlignCenter)

        self.telemetry_state_label = QLabel("NO DATA")
        self.telemetry_state_label.setAlignment(Qt.AlignCenter)

        layout.addWidget(title)
        layout.addStretch()
        layout.addWidget(self.port_combo)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.connection_label)
        layout.addWidget(self.system_status_label)
        layout.addWidget(self.telemetry_state_label)
        return layout

    def build_status_cards(self):
        layout = QGridLayout()

        self.temp_label = self.make_value_card("Temperature", "-- °F")
        self.press_label = self.make_value_card("Pressure", "-- hPa")
        self.hum_label = self.make_value_card("Humidity", "-- %")
        self.uptime_label = self.make_value_card("Uptime", "-- s")
        self.packet_label = self.make_value_card("Packets", "0")
        self.rate_label = self.make_value_card("Packet Rate", "0.00 Hz")

        layout.addWidget(self.temp_label["box"], 0, 0)
        layout.addWidget(self.press_label["box"], 0, 1)
        layout.addWidget(self.hum_label["box"], 0, 2)
        layout.addWidget(self.uptime_label["box"], 1, 0)
        layout.addWidget(self.packet_label["box"], 1, 1)
        layout.addWidget(self.rate_label["box"], 1, 2)
        return layout

    def build_health_bar(self):
        layout = QGridLayout()

        self.bme_health = self.make_value_card("BME280", "UNKNOWN")
        self.imu_health = self.make_value_card("IMU", "UNKNOWN")
        self.aux_health = self.make_value_card("AUX 0x29", "UNKNOWN")
        self.pitch_label = self.make_value_card("Pitch", "-- °")
        self.roll_label = self.make_value_card("Roll", "-- °")
        self.loss_label = self.make_value_card("Packet Loss", "0.00 %")

        layout.addWidget(self.bme_health["box"], 0, 0)
        layout.addWidget(self.imu_health["box"], 0, 1)
        layout.addWidget(self.aux_health["box"], 0, 2)
        layout.addWidget(self.pitch_label["box"], 0, 3)
        layout.addWidget(self.roll_label["box"], 0, 4)
        layout.addWidget(self.loss_label["box"], 0, 5)
        return layout

    def make_value_card(self, title, initial_value):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        value = QLabel(initial_value)
        value.setAlignment(Qt.AlignCenter)
        value.setStyleSheet("font-size: 20px; font-weight: bold;")
        layout.addWidget(value)
        return {"box": box, "value": value}

    def make_plot(self, title, left_label, units):
        plot = pg.PlotWidget(title=title)
        plot.setLabel("bottom", "Device Uptime", units="s")
        plot.setLabel("left", left_label, units=units)
        plot.showGrid(x=True, y=True, alpha=0.2)
        return plot

    def build_graph_section(self):
        layout = QGridLayout()

        self.temp_plot = self.make_plot("Temperature", "Temperature", "°F")
        self.press_plot = self.make_plot("Pressure", "Pressure", "hPa")
        self.hum_plot = self.make_plot("Humidity", "Humidity", "%")

        self.temp_curve = self.temp_plot.plot(name="Temperature")
        self.press_curve = self.press_plot.plot(name="Pressure")
        self.hum_curve = self.hum_plot.plot(name="Humidity")

        self.accel_plot = self.make_plot("Accelerometer", "Acceleration", "g")
        self.accel_plot.addLegend()
        self.ax_curve = self.accel_plot.plot(name="AX")
        self.ay_curve = self.accel_plot.plot(name="AY")
        self.az_curve = self.accel_plot.plot(name="AZ")

        self.gyro_plot = self.make_plot("Gyroscope", "Angular Rate", "°/s")
        self.gyro_plot.addLegend()
        self.gx_curve = self.gyro_plot.plot(name="GX")
        self.gy_curve = self.gyro_plot.plot(name="GY")
        self.gz_curve = self.gyro_plot.plot(name="GZ")

        layout.addWidget(self.temp_plot, 0, 0)
        layout.addWidget(self.press_plot, 0, 1)
        layout.addWidget(self.hum_plot, 0, 2)
        layout.addWidget(self.accel_plot, 1, 0, 1, 2)
        layout.addWidget(self.gyro_plot, 1, 2)
        return layout

    def build_diagnostics_panel(self):
        box = QGroupBox("Diagnostics")
        layout = QGridLayout(box)

        self.lost_packets_label = QLabel("0")
        self.malformed_packets_label = QLabel("0")
        self.reconnects_label = QLabel("0")
        self.min_temp_label = QLabel("--")
        self.max_temp_label = QLabel("--")
        self.peak_accel_label = QLabel("--")
        self.peak_gyro_label = QLabel("--")

        rows = [
            ("Lost packets", self.lost_packets_label),
            ("Malformed packets", self.malformed_packets_label),
            ("Connections", self.reconnects_label),
            ("Min temperature", self.min_temp_label),
            ("Max temperature", self.max_temp_label),
            ("Peak acceleration", self.peak_accel_label),
            ("Peak gyro", self.peak_gyro_label),
        ]

        for row, (name, value) in enumerate(rows):
            layout.addWidget(QLabel(name), row, 0)
            layout.addWidget(value, row, 1)

        return box

    def build_event_panel(self):
        box = QGroupBox("Event Log")
        layout = QVBoxLayout(box)
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        layout.addWidget(self.event_log)
        return box

    def build_command_bar(self):
        layout = QHBoxLayout()

        self.logging_button = QPushButton("Start Logging")
        self.logging_button.clicked.connect(self.toggle_logging)

        self.status_button = QPushButton("Request Status")
        self.status_button.clicked.connect(lambda: self.send_command(command_status()))

        self.pause_button = QPushButton("Pause")
        self.pause_button.clicked.connect(lambda: self.send_command(command_pause()))

        self.resume_button = QPushButton("Resume")
        self.resume_button.clicked.connect(lambda: self.send_command(command_resume()))

        self.rate_spin = QSpinBox()
        self.rate_spin.setRange(100, 10000)
        self.rate_spin.setValue(1000)
        self.rate_spin.setSuffix(" ms")

        self.rate_button = QPushButton("Set Rate")
        self.rate_button.clicked.connect(self.send_rate_command)

        self.inject_imu_button = QPushButton("Inject IMU Fault")
        self.inject_imu_button.clicked.connect(
            lambda: self.send_command(command_inject_fault("IMU"))
        )

        self.clear_faults_button = QPushButton("Clear Faults")
        self.clear_faults_button.clicked.connect(
            lambda: self.send_command(command_clear_faults())
        )

        self.reset_button = QPushButton("Reset Device")
        self.reset_button.clicked.connect(lambda: self.send_command(command_reset()))

        for widget in (
            self.logging_button, self.status_button, self.pause_button,
            self.resume_button, self.rate_spin, self.rate_button,
            self.inject_imu_button, self.clear_faults_button, self.reset_button,
        ):
            layout.addWidget(widget)

        return layout

    def process_serial(self):
        while True:
            line = self.serial_manager.get_line_nowait()
            if line is None:
                break
            self.on_serial_line(line)

        while True:
            event = self.serial_manager.get_event_nowait()
            if event is None:
                break

            event_type, value = event
            if event_type == "CONNECTED":
                self.on_connect(value)
            elif event_type == "DISCONNECTED":
                self.on_disconnect(value)
            elif event_type == "ERROR":
                self.on_serial_error(value)

    def refresh_ports(self):
        current_port = self.port_combo.currentData()
        self.port_combo.clear()

        ports = SerialManager.available_ports()
        for port in ports:
            description = f"{port['device']} - {port['description']}"
            self.port_combo.addItem(description, port["device"])

        if current_port:
            for index in range(self.port_combo.count()):
                if self.port_combo.itemData(index) == current_port:
                    self.port_combo.setCurrentIndex(index)
                    break

        if self.port_combo.count() == 0:
            self.port_combo.addItem("COM3", "COM3")

    def toggle_connection(self):
        if self.serial_manager.connected:
            self.serial_manager.disconnect()
            return

        port = self.port_combo.currentData() or self.port_combo.currentText()

        try:
            self.serial_manager.set_port(port)
            self.serial_manager.auto_reconnect = True
            if not self.serial_manager.connect():
                self.add_event("ERROR", f"Unable to connect to {port}")
        except Exception as error:
            self.add_event("ERROR", str(error))

    def on_connect(self, port):
        self.stats.register_reconnect()
        self.connection_label.setText("CONNECTED")
        self.connect_button.setText("Disconnect")
        self.add_event("INFO", f"Connected to {port}")

        if self.logger.logging_enabled:
            self.logger.log_event("INFO", "SERIAL_CONNECT", port)

    def on_disconnect(self, port):
        self.connection_label.setText("DISCONNECTED")
        self.telemetry_state_label.setText("NO DATA")
        self.connect_button.setText("Connect")
        self.add_event("WARN", f"Disconnected from {port}")

        if self.logger.logging_enabled:
            self.logger.log_event("WARN", "SERIAL_DISCONNECT", port)

    def on_serial_error(self, error):
        self.add_event("ERROR", str(error))
        if self.logger.logging_enabled:
            self.logger.log_event("ERROR", "SERIAL_ERROR", str(error))

    def on_serial_line(self, line):
        telemetry = parse_telemetry(line)

        if telemetry is not None:
            self.stats.update(telemetry)
            self.latest_data.update(telemetry)
            self.last_packet_wall_time = time.time()
            self.stale_reported = False
            self.append_history(telemetry)

            if self.logger.logging_enabled:
                self.logger.log_telemetry(telemetry)
            return

        if line.strip().startswith("TEL,"):
            self.stats.update(None)
            self.add_event("WARN", "Malformed telemetry packet")
            return

        response = parse_response(line)
        if not response or response.get("type") == "UNKNOWN":
            return

        response_type = response.get("type", "INFO")
        self.add_event(response_type, response.get("raw", line))

        if response_type == "STATUS":
            for key in ("STATE", "BME", "IMU", "AUX", "PAUSED", "RATE_MS", "FW"):
                if key in response:
                    self.latest_data[key] = response[key]

            if "STATE" in response:
                self.latest_data["STATUS"] = response["STATE"]

    def append_history(self, data):
        uptime = data.get("TIME")
        if uptime is None:
            return

        seconds = uptime / 1000.0
        self.time_history.append(seconds)
        self.temp_history.append(data.get("TEMP"))
        self.press_history.append(data.get("PRESS"))
        self.hum_history.append(data.get("HUM"))
        self.ax_history.append(data.get("AX"))
        self.ay_history.append(data.get("AY"))
        self.az_history.append(data.get("AZ"))
        self.gx_history.append(data.get("GX"))
        self.gy_history.append(data.get("GY"))
        self.gz_history.append(data.get("GZ"))

    @staticmethod
    def c_to_f(celsius):
        if celsius is None:
            return None
        return (celsius * 9.0 / 5.0) + 32.0

    @staticmethod
    def calculate_pitch_roll(data):
        ax = data.get("AX")
        ay = data.get("AY")
        az = data.get("AZ")

        if None in (ax, ay, az):
            return None, None

        pitch = math.degrees(math.atan2(-ax, math.sqrt(ay * ay + az * az)))
        roll = math.degrees(math.atan2(ay, az))
        return pitch, roll

    def refresh_gui(self):
        data = self.latest_data
        if not data:
            return

        temp = data.get("TEMP")
        press = data.get("PRESS")
        hum = data.get("HUM")
        uptime = data.get("TIME", 0.0)

        temp_f = self.c_to_f(temp)
        if temp_f is not None:
            self.temp_label["value"].setText(f"{temp_f:.2f} °F")
        if press is not None:
            self.press_label["value"].setText(f"{press:.2f} hPa")
        if hum is not None:
            self.hum_label["value"].setText(f"{hum:.2f} %")

        self.uptime_label["value"].setText(f"{uptime / 1000.0:.1f} s")
        self.packet_label["value"].setText(str(self.stats.total_packets))
        self.rate_label["value"].setText(f"{self.stats.packet_rate_hz:.2f} Hz")

        status = data.get("STATUS", data.get("STATE", "UNKNOWN"))
        self.system_status_label.setText(status)

        self.bme_health["value"].setText(data.get("BME", "UNKNOWN"))
        self.imu_health["value"].setText(data.get("IMU", "UNKNOWN"))
        self.aux_health["value"].setText(data.get("AUX", "UNKNOWN"))

        pitch, roll = self.calculate_pitch_roll(data)
        self.pitch_label["value"].setText("-- °" if pitch is None else f"{pitch:.1f} °")
        self.roll_label["value"].setText("-- °" if roll is None else f"{roll:.1f} °")

        total_expected = self.stats.total_packets + self.stats.lost_packets
        loss_pct = (
            (self.stats.lost_packets / total_expected) * 100.0
            if total_expected else 0.0
        )
        self.loss_label["value"].setText(f"{loss_pct:.2f} %")

        self.lost_packets_label.setText(str(self.stats.lost_packets))
        self.malformed_packets_label.setText(str(self.stats.malformed_packets))
        self.reconnects_label.setText(str(self.stats.serial_reconnects))

        if self.stats.min_temperature is not None:
            self.min_temp_label.setText(
                f"{self.c_to_f(self.stats.min_temperature):.2f} °F"
            )
        if self.stats.max_temperature is not None:
            self.max_temp_label.setText(
                f"{self.c_to_f(self.stats.max_temperature):.2f} °F"
            )

        self.peak_accel_label.setText(f"{self.stats.peak_acceleration:.3f} g")
        self.peak_gyro_label.setText(f"{self.stats.peak_gyro:.2f} °/s")

        self.refresh_telemetry_state()
        self.refresh_plots()

    def refresh_telemetry_state(self):
        if not self.serial_manager.connected:
            self.telemetry_state_label.setText("NO DATA")
            return

        if self.last_packet_wall_time is None:
            self.telemetry_state_label.setText("WAITING")
            return

        age = time.time() - self.last_packet_wall_time
        if age > STALE_TIMEOUT_SECONDS:
            self.telemetry_state_label.setText("STALE")
            if not self.stale_reported:
                self.add_event("WARN", f"Telemetry stale for {age:.1f} s")
                self.stale_reported = True
        else:
            self.telemetry_state_label.setText("LIVE")

    @staticmethod
    def valid_series(values, transform=None):
        output = []
        for value in values:
            if value is None:
                output.append(float("nan"))
            elif transform:
                output.append(transform(value))
            else:
                output.append(value)
        return output

    def refresh_plots(self):
        x = list(self.time_history)
        if not x:
            return

        self.temp_curve.setData(x, self.valid_series(self.temp_history, self.c_to_f))
        self.press_curve.setData(x, self.valid_series(self.press_history))
        self.hum_curve.setData(x, self.valid_series(self.hum_history))

        self.ax_curve.setData(x, self.valid_series(self.ax_history))
        self.ay_curve.setData(x, self.valid_series(self.ay_history))
        self.az_curve.setData(x, self.valid_series(self.az_history))

        self.gx_curve.setData(x, self.valid_series(self.gx_history))
        self.gy_curve.setData(x, self.valid_series(self.gy_history))
        self.gz_curve.setData(x, self.valid_series(self.gz_history))

    def toggle_logging(self):
        if self.logger.logging_enabled:
            self.logger.stop(
                stats=self.stats,
                device_info={
                    "port": self.serial_manager.port,
                    "baud": self.serial_manager.baud,
                },
            )
            self.logging_button.setText("Start Logging")
            self.add_event("INFO", "Logging stopped")
            return

        self.logger.start()
        self.logging_button.setText("Stop Logging")
        self.add_event("INFO", "Logging started")

    def send_command(self, command):
        success = self.serial_manager.send(command)

        if success:
            self.add_event("TX", command)
            if self.logger.logging_enabled:
                self.logger.log_event("INFO", "COMMAND_SENT", command)
        else:
            self.add_event("ERROR", f"Unable to send: {command}")

    def send_rate_command(self):
        try:
            self.send_command(command_set_rate(self.rate_spin.value()))
        except ValueError as error:
            self.add_event("ERROR", str(error))

    def add_event(self, level, message):
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.append(f"[{timestamp}] {level}: {message}")

    def closeEvent(self, event):
        if self.logger.logging_enabled:
            self.logger.stop(
                stats=self.stats,
                device_info={
                    "port": self.serial_manager.port,
                    "baud": self.serial_manager.baud,
                },
            )

        self.serial_manager.disconnect()
        event.accept()


def run():
    app = QApplication(sys.argv)
    window = GroundStationWindow()
    window.show()
    sys.exit(app.exec())
