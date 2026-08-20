import math
import sys
import time
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ground_station.attitude import AttitudePanel
from ground_station.logger import TelemetryLogger
from ground_station.parser import parse_telemetry
from ground_station.protocol import (
    command_clear_faults,
    command_inject_fault,
    command_pause,
    command_reset,
    command_resume,
    command_set_rate,
    command_status,
    parse_response,
)
from ground_station.serial_manager import SerialManager
from ground_station.stats import TelemetryStats

MAX_POINTS = 180
DEFAULT_STALE_TIMEOUT_SECONDS = 3.0


class GroundStationWindow(QMainWindow):
    def __init__(self, serial_manager=None):
        super().__init__()
        self.setWindowTitle("Embedded Telemetry Ground Station")
        self.resize(1500, 930)

        self.stats = TelemetryStats()
        self.logger = TelemetryLogger()
        self.latest_data = {}
        self.last_packet_wall_time = None
        self.stale_reported = False
        self.commanded_rate_ms = 1000
        self.device_paused = False

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

        self.serial_manager = serial_manager or SerialManager(port="COM3", baud=115200)

        self.build_ui()

        self.gui_timer = QTimer(self)
        self.gui_timer.timeout.connect(self.process_serial)
        self.gui_timer.timeout.connect(self.refresh_gui)
        self.gui_timer.start(100)

        self.refresh_ports()
        self.update_control_state()

    def build_ui(self):
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        dashboard = QWidget()
        dashboard_layout = QVBoxLayout(dashboard)
        dashboard_layout.setContentsMargins(8, 6, 8, 6)
        dashboard_layout.setSpacing(5)

        dashboard_layout.addLayout(self.build_connection_bar())
        dashboard_layout.addLayout(self.build_status_cards())
        dashboard_layout.addLayout(self.build_health_bar())
        dashboard_layout.addLayout(self.build_graph_section(), 1)

        lower_layout = QHBoxLayout()
        lower_layout.addWidget(self.build_diagnostics_panel(), 1)
        lower_layout.addWidget(self.build_event_panel(), 2)
        dashboard_layout.addLayout(lower_layout)
        dashboard_layout.addLayout(self.build_command_bar())

        raw_tab = QWidget()
        raw_layout = QVBoxLayout(raw_tab)
        raw_layout.setContentsMargins(8, 8, 8, 8)

        raw_header = QHBoxLayout()
        raw_header.addWidget(QLabel("Raw serial traffic"))
        raw_header.addStretch()
        clear_raw = QPushButton("Clear Raw Log")
        clear_raw.clicked.connect(lambda: self.raw_log.clear())
        raw_header.addWidget(clear_raw)
        raw_layout.addLayout(raw_header)

        self.raw_log = QPlainTextEdit()
        self.raw_log.setReadOnly(True)
        self.raw_log.document().setMaximumBlockCount(1500)
        raw_layout.addWidget(self.raw_log)

        self.attitude_panel = AttitudePanel()

        tabs.addTab(dashboard, "Dashboard")
        tabs.addTab(self.attitude_panel, "Attitude")
        tabs.addTab(raw_tab, "Raw Telemetry")

    def build_connection_bar(self):
        layout = QHBoxLayout()

        title = QLabel("EMBEDDED TELEMETRY GROUND STATION")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")

        self.port_combo = QComboBox()
        self.refresh_button = QPushButton("Refresh Ports")
        self.refresh_button.clicked.connect(self.refresh_ports)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.toggle_connection)

        self.connection_label = QLabel("DISCONNECTED")
        self.system_status_label = QLabel("UNKNOWN")
        self.telemetry_state_label = QLabel("NO DATA")

        for label in (
            self.connection_label,
            self.system_status_label,
            self.telemetry_state_label,
        ):
            label.setAlignment(Qt.AlignCenter)
            label.setMinimumWidth(72)
            label.setStyleSheet("font-weight: 700; padding: 3px 6px;")

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
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(2)

        self.temp_label = self.make_value_card("Temperature", "-- °F", compact=True)
        self.press_label = self.make_value_card("Pressure", "-- hPa", compact=True)
        self.hum_label = self.make_value_card("Humidity", "-- %", compact=True)
        self.uptime_label = self.make_value_card("Uptime", "-- s", compact=True)
        self.packet_label = self.make_value_card("Packets", "0", compact=True)
        self.rate_label = self.make_value_card("Avg Packet Rate", "0.00 Hz", compact=True)

        cards = (
            self.temp_label,
            self.press_label,
            self.hum_label,
            self.uptime_label,
            self.packet_label,
            self.rate_label,
        )

        for column, card in enumerate(cards):
            layout.addWidget(card["box"], 0, column)

        return layout

    def build_health_bar(self):
        layout = QGridLayout()
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(2)

        self.bme_health = self.make_value_card("BME280", "UNKNOWN", compact=True)
        self.imu_health = self.make_value_card("IMU", "UNKNOWN", compact=True)
        self.aux_health = self.make_value_card("AUX 0x29", "UNKNOWN", compact=True)
        self.pitch_label = self.make_value_card("Pitch", "-- °", compact=True)
        self.roll_label = self.make_value_card("Roll", "-- °", compact=True)
        self.loss_label = self.make_value_card("Packet Loss", "0.00 %", compact=True)

        cards = (
            self.bme_health,
            self.imu_health,
            self.aux_health,
            self.pitch_label,
            self.roll_label,
            self.loss_label,
        )

        for column, card in enumerate(cards):
            layout.addWidget(card["box"], 0, column)

        return layout

    def make_value_card(self, title, initial_value, compact=False):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(7, 3, 7, 4)
        layout.setSpacing(0)

        value = QLabel(initial_value)
        value.setAlignment(Qt.AlignCenter)
        value.setStyleSheet(
            f"font-size: {'16px' if compact else '18px'}; font-weight: 700;"
        )
        layout.addWidget(value)

        if compact:
            box.setMaximumHeight(58)
            box.setMinimumHeight(50)

        return {"box": box, "value": value}

    def make_plot(self, title, left_label, units):
        plot = pg.PlotWidget(title=title)
        plot.setLabel("bottom", "Device Uptime", units="s")
        plot.setLabel("left", left_label, units=units)
        plot.showGrid(x=True, y=True, alpha=0.2)
        return plot

    def build_graph_section(self):
        layout = QGridLayout()
        layout.setSpacing(5)

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
        box = QGroupBox("Diagnostics / Device")
        layout = QGridLayout(box)
        layout.setVerticalSpacing(2)

        labels = {
            "lost": ("Lost packets", "0"),
            "malformed": ("Malformed packets", "0"),
            "connections": ("Connections", "0"),
            "duration": ("Session duration", "0.0 s"),
            "min_temp": ("Min temperature", "--"),
            "max_temp": ("Max temperature", "--"),
            "peak_accel": ("Peak acceleration", "--"),
            "peak_gyro": ("Peak gyro", "--"),
            "fw": ("Firmware", "--"),
            "rate": ("Device rate", "--"),
            "paused": ("Paused", "--"),
            "i2c": ("I2C errors", "0"),
            "recovery": ("Recoveries", "0"),
            "bme_fail": ("BME failures", "0"),
            "imu_fail": ("IMU failures", "0"),
            "crc": ("CRC", "--"),
        }

        self.diag_values = {}
        items = list(labels.items())

        for index, (key, (name, initial)) in enumerate(items):
            column_pair = 0 if index < 8 else 2
            row = index if index < 8 else index - 8
            value = QLabel(initial)
            self.diag_values[key] = value
            layout.addWidget(QLabel(name), row, column_pair)
            layout.addWidget(value, row, column_pair + 1)

        return box

    def build_event_panel(self):
        box = QGroupBox("Event Log")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(6, 6, 6, 6)
        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.document().setMaximumBlockCount(500)
        layout.addWidget(self.event_log)
        return box

    def build_command_bar(self):
        layout = QHBoxLayout()
        layout.setSpacing(5)

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

        self.inject_imu_button = QPushButton("Fault IMU")
        self.inject_imu_button.clicked.connect(
            lambda: self.send_command(command_inject_fault("IMU"))
        )

        self.inject_bme_button = QPushButton("Fault BME")
        self.inject_bme_button.clicked.connect(
            lambda: self.send_command(command_inject_fault("BME"))
        )

        self.clear_faults_button = QPushButton("Clear Faults")
        self.clear_faults_button.clicked.connect(
            lambda: self.send_command(command_clear_faults())
        )

        self.reset_stats_button = QPushButton("Reset Stats")
        self.reset_stats_button.clicked.connect(self.reset_statistics)

        self.reset_button = QPushButton("Reset Device")
        self.reset_button.clicked.connect(lambda: self.send_command(command_reset()))

        self.device_controls = [
            self.status_button,
            self.pause_button,
            self.resume_button,
            self.rate_spin,
            self.rate_button,
            self.inject_imu_button,
            self.inject_bme_button,
            self.clear_faults_button,
            self.reset_button,
        ]

        for widget in (
            self.logging_button,
            self.status_button,
            self.pause_button,
            self.resume_button,
            self.rate_spin,
            self.rate_button,
            self.inject_imu_button,
            self.inject_bme_button,
            self.clear_faults_button,
            self.reset_stats_button,
            self.reset_button,
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

        ports = self.serial_manager.available_ports()
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
        self.update_control_state()

        if self.logger.logging_enabled:
            self.logger.log_event("INFO", "SERIAL_CONNECT", port)

        QTimer.singleShot(250, lambda: self.send_command(command_status()))

    def on_disconnect(self, port):
        self.connection_label.setText("DISCONNECTED")
        self.telemetry_state_label.setText("NO DATA")
        self.connect_button.setText("Connect")
        self.device_paused = False
        self.add_event("WARN", f"Disconnected from {port}")
        self.update_control_state()

        if self.logger.logging_enabled:
            self.logger.log_event("WARN", "SERIAL_DISCONNECT", port)

    def on_serial_error(self, error):
        self.add_event("ERROR", str(error))
        if self.logger.logging_enabled:
            self.logger.log_event("ERROR", "SERIAL_ERROR", str(error))

    def on_serial_line(self, line):
        timestamp = time.strftime("%H:%M:%S")
        self.raw_log.appendPlainText(f"[{timestamp}] RX {line}")

        telemetry = parse_telemetry(line)
        if telemetry is not None:
            self._remove_stale_sensor_values(telemetry)
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
            self.add_event("WARN", "Malformed or CRC-invalid telemetry packet")
            return

        response = parse_response(line)
        if not response or response.get("type") == "UNKNOWN":
            return

        response_type = response.get("type", "INFO")
        self.add_event(response_type, response.get("raw", line))

        if response_type == "STATUS":
            self._apply_status_response(response)

    def _apply_status_response(self, response):
        for key, value in response.items():
            if key not in {"type", "raw"}:
                self.latest_data[key] = value

        if "STATE" in response:
            self.latest_data["STATUS"] = response["STATE"]
        if "RATE_MS" in response:
            try:
                self.commanded_rate_ms = int(response["RATE_MS"])
                self.rate_spin.setValue(self.commanded_rate_ms)
            except ValueError:
                pass
        if "PAUSED" in response:
            self.device_paused = response["PAUSED"] == "1"

    def _remove_stale_sensor_values(self, telemetry):
        if telemetry.get("BME") == "FAULT":
            for key in ("TEMP", "PRESS", "HUM"):
                self.latest_data.pop(key, None)

        if telemetry.get("IMU") == "FAULT":
            for key in ("AX", "AY", "AZ", "GX", "GY", "GZ"):
                self.latest_data.pop(key, None)

    @staticmethod
    def _history_value(data, key):
        value = data.get(key)
        return float("nan") if value is None else value

    def append_history(self, data):
        uptime = data.get("TIME")
        if uptime is None:
            return

        self.time_history.append(uptime / 1000.0)
        self.temp_history.append(self._history_value(data, "TEMP"))
        self.press_history.append(self._history_value(data, "PRESS"))
        self.hum_history.append(self._history_value(data, "HUM"))
        self.ax_history.append(self._history_value(data, "AX"))
        self.ay_history.append(self._history_value(data, "AY"))
        self.az_history.append(self._history_value(data, "AZ"))
        self.gx_history.append(self._history_value(data, "GX"))
        self.gy_history.append(self._history_value(data, "GY"))
        self.gz_history.append(self._history_value(data, "GZ"))

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
        self.refresh_connection_styles()
        self.refresh_telemetry_state()

        data = self.latest_data
        if not data:
            self.attitude_panel.set_attitude(None, None, False)
            return

        temp_f = self.c_to_f(data.get("TEMP"))
        self.temp_label["value"].setText("-- °F" if temp_f is None else f"{temp_f:.2f} °F")

        press = data.get("PRESS")
        self.press_label["value"].setText("-- hPa" if press is None else f"{press:.2f} hPa")

        hum = data.get("HUM")
        self.hum_label["value"].setText("-- %" if hum is None else f"{hum:.2f} %")

        uptime = data.get("TIME")
        self.uptime_label["value"].setText("-- s" if uptime is None else f"{uptime / 1000.0:.1f} s")
        self.packet_label["value"].setText(str(self.stats.total_packets))
        self.rate_label["value"].setText(f"{self.stats.average_packet_rate_hz:.2f} Hz")
        self.loss_label["value"].setText(f"{self.stats.packet_loss_percent:.2f} %")

        status = data.get("STATUS", data.get("STATE", "UNKNOWN"))
        self.system_status_label.setText(status)
        self.style_state_label(self.system_status_label, status)

        bme = data.get("BME", "UNKNOWN")
        imu = data.get("IMU", "UNKNOWN")
        aux = data.get("AUX", "UNKNOWN")
        self.bme_health["value"].setText(bme)
        self.imu_health["value"].setText(imu)
        self.aux_health["value"].setText(aux)
        self.style_health_card(self.bme_health, bme)
        self.style_health_card(self.imu_health, imu)
        self.style_health_card(self.aux_health, aux)

        pitch, roll = self.calculate_pitch_roll(data)
        attitude_valid = pitch is not None and roll is not None and imu == "OK"
        self.pitch_label["value"].setText("-- °" if pitch is None else f"{pitch:.1f} °")
        self.roll_label["value"].setText("-- °" if roll is None else f"{roll:.1f} °")
        self.attitude_panel.set_attitude(pitch, roll, attitude_valid)

        self.refresh_diagnostics(data)
        self.refresh_plots()

    def refresh_diagnostics(self, data):
        values = self.diag_values
        values["lost"].setText(str(self.stats.lost_packets))
        values["malformed"].setText(str(self.stats.malformed_packets))
        values["connections"].setText(str(self.stats.serial_reconnects))
        values["duration"].setText(f"{self.stats.session_duration_seconds:.1f} s")

        min_temp = self.c_to_f(self.stats.min_temperature)
        max_temp = self.c_to_f(self.stats.max_temperature)
        values["min_temp"].setText("--" if min_temp is None else f"{min_temp:.2f} °F")
        values["max_temp"].setText("--" if max_temp is None else f"{max_temp:.2f} °F")
        values["peak_accel"].setText(f"{self.stats.peak_acceleration:.3f} g")
        values["peak_gyro"].setText(f"{self.stats.peak_gyro:.2f} °/s")

        values["fw"].setText(str(data.get("FW", "--")))
        values["rate"].setText(f"{self.commanded_rate_ms} ms")
        values["paused"].setText("YES" if self.device_paused else "NO")
        values["i2c"].setText(str(int(float(data.get("I2C_ERR", 0) or 0))))
        values["recovery"].setText(str(int(float(data.get("RECOVERY", 0) or 0))))
        values["bme_fail"].setText(str(int(float(data.get("BME_FAIL", 0) or 0))))
        values["imu_fail"].setText(str(int(float(data.get("IMU_FAIL", 0) or 0))))
        values["crc"].setText("VALID" if data.get("CRC_VALID") else "LEGACY")

    def refresh_plots(self):
        x = list(self.time_history)
        if not x:
            return

        temp_f_history = [
            self.c_to_f(value) if not math.isnan(value) else float("nan")
            for value in self.temp_history
        ]

        self.temp_curve.setData(x, temp_f_history)
        self.press_curve.setData(x, list(self.press_history))
        self.hum_curve.setData(x, list(self.hum_history))
        self.ax_curve.setData(x, list(self.ax_history))
        self.ay_curve.setData(x, list(self.ay_history))
        self.az_curve.setData(x, list(self.az_history))
        self.gx_curve.setData(x, list(self.gx_history))
        self.gy_curve.setData(x, list(self.gy_history))
        self.gz_curve.setData(x, list(self.gz_history))

    def refresh_connection_styles(self):
        connected = self.serial_manager.connected
        self.connection_label.setText("CONNECTED" if connected else "DISCONNECTED")
        self.connection_label.setStyleSheet(
            self.label_style("#153d24", "#8ff0a4") if connected
            else self.label_style("#3d1c1c", "#ff9b9b")
        )

    def refresh_telemetry_state(self):
        if not self.serial_manager.connected:
            self.telemetry_state_label.setText("NO DATA")
            self.telemetry_state_label.setStyleSheet(self.label_style("#2b2b2b", "#bdbdbd"))
            return

        if self.device_paused:
            self.telemetry_state_label.setText("PAUSED")
            self.telemetry_state_label.setStyleSheet(self.label_style("#3b3517", "#ffe58a"))
            return

        if self.last_packet_wall_time is None:
            self.telemetry_state_label.setText("WAITING")
            self.telemetry_state_label.setStyleSheet(self.label_style("#2b2b2b", "#bdbdbd"))
            return

        timeout = max(
            DEFAULT_STALE_TIMEOUT_SECONDS,
            (self.commanded_rate_ms / 1000.0) * 3.0,
        )
        age = time.time() - self.last_packet_wall_time

        if age > timeout:
            self.telemetry_state_label.setText("STALE")
            self.telemetry_state_label.setStyleSheet(self.label_style("#4a2811", "#ffbd76"))
            if not self.stale_reported:
                self.stale_reported = True
                self.add_event("WARN", f"Telemetry stale for {age:.1f} s")
        else:
            self.telemetry_state_label.setText("LIVE")
            self.telemetry_state_label.setStyleSheet(self.label_style("#153d24", "#8ff0a4"))

    @staticmethod
    def label_style(background, foreground):
        return (
            f"font-weight: 700; padding: 3px 6px; border-radius: 4px; "
            f"background: {background}; color: {foreground};"
        )

    def style_state_label(self, label, state):
        styles = {
            "NORMAL": ("#153d24", "#8ff0a4"),
            "DEGRADED": ("#4a3811", "#ffe08a"),
            "FAULT": ("#4a1818", "#ff8d8d"),
        }
        background, foreground = styles.get(state, ("#2b2b2b", "#bdbdbd"))
        label.setStyleSheet(self.label_style(background, foreground))

    def style_health_card(self, card, state):
        styles = {
            "OK": ("#153d24", "#8ff0a4"),
            "PRESENT": ("#15333d", "#91d7f5"),
            "FAULT": ("#4a1818", "#ff8d8d"),
            "ABSENT": ("#4a3811", "#ffe08a"),
        }
        background, foreground = styles.get(state, ("#2b2b2b", "#bdbdbd"))
        card["value"].setStyleSheet(
            f"font-size: 16px; font-weight: 700; color: {foreground};"
        )
        card["box"].setStyleSheet(
            f"QGroupBox {{ background: {background}; border-radius: 4px; }}"
        )

    def update_control_state(self):
        connected = self.serial_manager.connected
        for widget in self.device_controls:
            widget.setEnabled(connected)
        self.logging_button.setEnabled(connected or self.logger.logging_enabled)

    def reset_statistics(self):
        connections = self.stats.serial_reconnects
        self.stats.reset()
        self.stats.serial_reconnects = connections
        self.add_event("INFO", "Ground-station statistics reset")

    def toggle_logging(self):
        if self.logger.logging_enabled:
            self.logger.stop(
                stats=self.stats,
                device_info=self.device_info(),
            )
            self.logging_button.setText("Start Logging")
            self.add_event("INFO", "Logging stopped")
            return

        self.logger.start()
        self.logging_button.setText("Stop Logging")
        self.add_event("INFO", "Logging started")

    def device_info(self):
        return {
            "port": self.serial_manager.port,
            "baud": self.serial_manager.baud,
            "firmware": self.latest_data.get("FW"),
            "rate_ms": self.commanded_rate_ms,
        }

    def send_command(self, command):
        success = self.serial_manager.send(command)
        timestamp = time.strftime("%H:%M:%S")
        self.raw_log.appendPlainText(f"[{timestamp}] TX {command}")

        if success:
            self.add_event("TX", command)
            if self.logger.logging_enabled:
                self.logger.log_event("INFO", "COMMAND_SENT", command)
        else:
            self.add_event("ERROR", f"Unable to send: {command}")

    def send_rate_command(self):
        try:
            command = command_set_rate(self.rate_spin.value())
            self.send_command(command)
        except ValueError as error:
            self.add_event("ERROR", str(error))

    def add_event(self, level, message):
        timestamp = time.strftime("%H:%M:%S")
        self.event_log.append(f"[{timestamp}] {level}: {message}")

    def closeEvent(self, event):
        if self.logger.logging_enabled:
            self.logger.stop(
                stats=self.stats,
                device_info=self.device_info(),
            )

        self.serial_manager.disconnect()
        event.accept()


def run(serial_manager=None):
    app = QApplication(sys.argv)
    window = GroundStationWindow(serial_manager=serial_manager)
    window.show()
    sys.exit(app.exec())
