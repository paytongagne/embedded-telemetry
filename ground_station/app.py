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
    QPushButton,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

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


MAX_POINTS = 120


class GroundStationWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Embedded Telemetry Ground Station")
        self.resize(1400, 900)

        self.stats = TelemetryStats()
        self.logger = TelemetryLogger()

        self.latest_data = {}
        self.last_packet_wall_time = None

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

        self.serial_manager = SerialManager(
            port="COM3",
            baud=115200,
        )

        self.build_ui()

        self.gui_timer = QTimer(self)
        self.gui_timer.timeout.connect(self.process_serial)
        self.gui_timer.timeout.connect(self.refresh_gui)
        self.gui_timer.start(100)

        self.refresh_ports()

    # ---------------------------------------------------------
    # UI
    # ---------------------------------------------------------

    def build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)

        main_layout.addLayout(self.build_connection_bar())
        main_layout.addLayout(self.build_status_cards())
        main_layout.addLayout(self.build_graph_section())

        lower_layout = QHBoxLayout()

        lower_layout.addWidget(
            self.build_diagnostics_panel(),
            1,
        )

        lower_layout.addWidget(
            self.build_event_panel(),
            2,
        )

        main_layout.addLayout(lower_layout)
        main_layout.addLayout(self.build_command_bar())

    def build_connection_bar(self):
        layout = QHBoxLayout()

        title = QLabel(
            "EMBEDDED TELEMETRY GROUND STATION"
        )

        title.setStyleSheet(
            "font-size: 20px; font-weight: bold;"
        )

        self.port_combo = QComboBox()

        self.refresh_button = QPushButton(
            "Refresh Ports"
        )

        self.refresh_button.clicked.connect(
            self.refresh_ports
        )

        self.connect_button = QPushButton(
            "Connect"
        )

        self.connect_button.clicked.connect(
            self.toggle_connection
        )

        self.connection_label = QLabel(
            "DISCONNECTED"
        )

        self.connection_label.setAlignment(
            Qt.AlignCenter
        )

        self.system_status_label = QLabel(
            "UNKNOWN"
        )

        self.system_status_label.setAlignment(
            Qt.AlignCenter
        )

        layout.addWidget(title)
        layout.addStretch()

        layout.addWidget(self.port_combo)
        layout.addWidget(self.refresh_button)
        layout.addWidget(self.connect_button)
        layout.addWidget(self.connection_label)
        layout.addWidget(self.system_status_label)

        return layout

    def build_status_cards(self):
        layout = QGridLayout()

        self.temp_label = self.make_value_card(
            "Temperature",
            "-- °F",
        )

        self.press_label = self.make_value_card(
            "Pressure",
            "-- hPa",
        )

        self.hum_label = self.make_value_card(
            "Humidity",
            "-- %",
        )

        self.uptime_label = self.make_value_card(
            "Uptime",
            "-- s",
        )

        self.packet_label = self.make_value_card(
            "Packets",
            "0",
        )

        self.rate_label = self.make_value_card(
            "Packet Rate",
            "0.00 Hz",
        )

        layout.addWidget(
            self.temp_label["box"],
            0,
            0,
        )

        layout.addWidget(
            self.press_label["box"],
            0,
            1,
        )

        layout.addWidget(
            self.hum_label["box"],
            0,
            2,
        )

        layout.addWidget(
            self.uptime_label["box"],
            1,
            0,
        )

        layout.addWidget(
            self.packet_label["box"],
            1,
            1,
        )

        layout.addWidget(
            self.rate_label["box"],
            1,
            2,
        )

        return layout

    def make_value_card(
        self,
        title,
        initial_value,
    ):
        box = QGroupBox(title)
        layout = QVBoxLayout(box)

        value = QLabel(initial_value)

        value.setAlignment(
            Qt.AlignCenter
        )

        value.setStyleSheet(
            "font-size: 22px; "
            "font-weight: bold;"
        )

        layout.addWidget(value)

        return {
            "box": box,
            "value": value,
        }

    def build_graph_section(self):
        layout = QGridLayout()

        # Environment
        self.environment_plot = pg.PlotWidget(
            title="Environment"
        )

        self.environment_plot.setLabel(
            "bottom",
            "Device Uptime",
            units="s",
        )

        self.environment_plot.showGrid(
            x=True,
            y=True,
            alpha=0.2,
        )

        self.environment_plot.addLegend()

        self.temp_curve = self.environment_plot.plot(
            name="Temperature"
        )

        self.press_curve = self.environment_plot.plot(
            name="Pressure"
        )

        self.hum_curve = self.environment_plot.plot(
            name="Humidity"
        )

        # Accelerometer
        self.accel_plot = pg.PlotWidget(
            title="Accelerometer"
        )

        self.accel_plot.setLabel(
            "bottom",
            "Device Uptime",
            units="s",
        )

        self.accel_plot.setLabel(
            "left",
            "Acceleration",
            units="g",
        )

        self.accel_plot.showGrid(
            x=True,
            y=True,
            alpha=0.2,
        )

        self.accel_plot.addLegend()

        self.ax_curve = self.accel_plot.plot(
            name="AX"
        )

        self.ay_curve = self.accel_plot.plot(
            name="AY"
        )

        self.az_curve = self.accel_plot.plot(
            name="AZ"
        )

        # Gyroscope
        self.gyro_plot = pg.PlotWidget(
            title="Gyroscope"
        )

        self.gyro_plot.setLabel(
            "bottom",
            "Device Uptime",
            units="s",
        )

        self.gyro_plot.setLabel(
            "left",
            "Angular Rate",
            units="°/s",
        )

        self.gyro_plot.showGrid(
            x=True,
            y=True,
            alpha=0.2,
        )

        self.gyro_plot.addLegend()

        self.gx_curve = self.gyro_plot.plot(
            name="GX"
        )

        self.gy_curve = self.gyro_plot.plot(
            name="GY"
        )

        self.gz_curve = self.gyro_plot.plot(
            name="GZ"
        )

        layout.addWidget(
            self.environment_plot,
            0,
            0,
            1,
            2,
        )

        layout.addWidget(
            self.accel_plot,
            1,
            0,
        )

        layout.addWidget(
            self.gyro_plot,
            1,
            1,
        )

        return layout

    def build_diagnostics_panel(self):
        box = QGroupBox(
            "Diagnostics"
        )

        layout = QGridLayout(box)

        self.lost_packets_label = QLabel("0")
        self.malformed_packets_label = QLabel("0")
        self.reconnects_label = QLabel("0")

        self.min_temp_label = QLabel("--")
        self.max_temp_label = QLabel("--")

        self.peak_accel_label = QLabel("--")
        self.peak_gyro_label = QLabel("--")

        rows = [
            (
                "Lost packets",
                self.lost_packets_label,
            ),
            (
                "Malformed packets",
                self.malformed_packets_label,
            ),
            (
                "Connections",
                self.reconnects_label,
            ),
            (
                "Min temperature",
                self.min_temp_label,
            ),
            (
                "Max temperature",
                self.max_temp_label,
            ),
            (
                "Peak acceleration",
                self.peak_accel_label,
            ),
            (
                "Peak gyro",
                self.peak_gyro_label,
            ),
        ]

        for row, (
            name,
            value,
        ) in enumerate(rows):
            layout.addWidget(
                QLabel(name),
                row,
                0,
            )

            layout.addWidget(
                value,
                row,
                1,
            )

        return box

    def build_event_panel(self):
        box = QGroupBox(
            "Event Log"
        )

        layout = QVBoxLayout(box)

        self.event_log = QTextEdit()
        self.event_log.setReadOnly(True)

        layout.addWidget(
            self.event_log
        )

        return box

    def build_command_bar(self):
        layout = QHBoxLayout()

        self.logging_button = QPushButton(
            "Start Logging"
        )

        self.logging_button.clicked.connect(
            self.toggle_logging
        )

        self.status_button = QPushButton(
            "Request Status"
        )

        self.status_button.clicked.connect(
            lambda: self.send_command(
                command_status()
            )
        )

        self.pause_button = QPushButton(
            "Pause"
        )

        self.pause_button.clicked.connect(
            lambda: self.send_command(
                command_pause()
            )
        )

        self.resume_button = QPushButton(
            "Resume"
        )

        self.resume_button.clicked.connect(
            lambda: self.send_command(
                command_resume()
            )
        )

        self.rate_spin = QSpinBox()

        self.rate_spin.setRange(
            100,
            10000,
        )

        self.rate_spin.setValue(
            1000
        )

        self.rate_spin.setSuffix(
            " ms"
        )

        self.rate_button = QPushButton(
            "Set Rate"
        )

        self.rate_button.clicked.connect(
            self.send_rate_command
        )

        self.inject_imu_button = QPushButton(
            "Inject IMU Fault"
        )

        self.inject_imu_button.clicked.connect(
            lambda: self.send_command(
                command_inject_fault(
                    "IMU"
                )
            )
        )

        self.clear_faults_button = QPushButton(
            "Clear Faults"
        )

        self.clear_faults_button.clicked.connect(
            lambda: self.send_command(
                command_clear_faults()
            )
        )

        self.reset_button = QPushButton(
            "Reset Device"
        )

        self.reset_button.clicked.connect(
            lambda: self.send_command(
                command_reset()
            )
        )

        layout.addWidget(
            self.logging_button
        )

        layout.addWidget(
            self.status_button
        )

        layout.addWidget(
            self.pause_button
        )

        layout.addWidget(
            self.resume_button
        )

        layout.addWidget(
            self.rate_spin
        )

        layout.addWidget(
            self.rate_button
        )

        layout.addWidget(
            self.inject_imu_button
        )

        layout.addWidget(
            self.clear_faults_button
        )

        layout.addWidget(
            self.reset_button
        )

        return layout

    # ---------------------------------------------------------
    # Serial queue processing
    # ---------------------------------------------------------

    def process_serial(self):
        while True:
            line = (
                self.serial_manager
                .get_line_nowait()
            )

            if line is None:
                break

            self.on_serial_line(line)

        while True:
            event = (
                self.serial_manager
                .get_event_nowait()
            )

            if event is None:
                break

            event_type, value = event

            if event_type == "CONNECTED":
                self.on_connect(value)

            elif event_type == "DISCONNECTED":
                self.on_disconnect(value)

            elif event_type == "ERROR":
                self.on_serial_error(value)

    # ---------------------------------------------------------
    # Connection management
    # ---------------------------------------------------------

    def refresh_ports(self):
        current = (
            self.port_combo
            .currentText()
        )

        self.port_combo.clear()

        ports = (
            SerialManager
            .available_ports()
        )

        for port in ports:
            description = (
                f"{port['device']} - "
                f"{port['description']}"
            )

            self.port_combo.addItem(
                description,
                port["device"],
            )

        if current:
            for index in range(
                self.port_combo.count()
            ):
                if (
                    self.port_combo
                    .itemText(index)
                    == current
                ):
                    self.port_combo.setCurrentIndex(
                        index
                    )
                    break

        if self.port_combo.count() == 0:
            self.port_combo.addItem(
                "COM3",
                "COM3",
            )

    def toggle_connection(self):
        if self.serial_manager.connected:
            self.serial_manager.disconnect()
            return

        port = (
            self.port_combo
            .currentData()
        )

        if not port:
            port = (
                self.port_combo
                .currentText()
            )

        try:
            self.serial_manager.set_port(
                port
            )

            self.serial_manager.auto_reconnect = True

            connected = (
                self.serial_manager
                .connect()
            )

            if not connected:
                self.add_event(
                    "ERROR",
                    f"Unable to connect to {port}",
                )

        except Exception as error:
            self.add_event(
                "ERROR",
                str(error),
            )

    def on_connect(self, port):
        self.stats.register_reconnect()

        self.connection_label.setText(
            "CONNECTED"
        )

        self.connection_label.setStyleSheet(
            "font-weight: bold;"
        )

        self.connect_button.setText(
            "Disconnect"
        )

        self.add_event(
            "INFO",
            f"Connected to {port}",
        )

        if self.logger.logging_enabled:
            self.logger.log_event(
                "INFO",
                "SERIAL_CONNECT",
                port,
            )

    def on_disconnect(self, port):
        self.connection_label.setText(
            "DISCONNECTED"
        )

        self.connect_button.setText(
            "Connect"
        )

        self.add_event(
            "WARN",
            f"Disconnected from {port}",
        )

        if self.logger.logging_enabled:
            self.logger.log_event(
                "WARN",
                "SERIAL_DISCONNECT",
                port,
            )

    def on_serial_error(self, error):
        self.add_event(
            "ERROR",
            str(error),
        )

        if self.logger.logging_enabled:
            self.logger.log_event(
                "ERROR",
                "SERIAL_ERROR",
                str(error),
            )

    # ---------------------------------------------------------
    # Incoming telemetry
    # ---------------------------------------------------------

    def on_serial_line(self, line):
        telemetry = parse_telemetry(
            line
        )

        if telemetry is not None:
            self.stats.update(
                telemetry
            )

            self.latest_data = telemetry

            self.last_packet_wall_time = (
                time.time()
            )

            self.append_history(
                telemetry
            )

            if self.logger.logging_enabled:
                self.logger.log_telemetry(
                    telemetry
                )

            return

        response = parse_response(
            line
        )

        if (
            response
            and response.get("type")
            != "UNKNOWN"
        ):
            self.add_event(
                response.get(
                    "type",
                    "INFO",
                ),
                response.get(
                    "raw",
                    line,
                ),
            )

    def append_history(self, data):
        uptime = data.get("TIME")

        if uptime is None:
            return

        seconds = (
            uptime / 1000.0
        )

        self.time_history.append(
            seconds
        )

        self.temp_history.append(
            data.get("TEMP", 0.0)
        )

        self.press_history.append(
            data.get("PRESS", 0.0)
        )

        self.hum_history.append(
            data.get("HUM", 0.0)
        )

        self.ax_history.append(
            data.get("AX", 0.0)
        )

        self.ay_history.append(
            data.get("AY", 0.0)
        )

        self.az_history.append(
            data.get("AZ", 0.0)
        )

        self.gx_history.append(
            data.get("GX", 0.0)
        )

        self.gy_history.append(
            data.get("GY", 0.0)
        )

        self.gz_history.append(
            data.get("GZ", 0.0)
        )


    def c_to_f(self, celsius):
        if celsius is None:
            return None

        return (celsius * 9.0 / 5.0) + 32.0

    def g_to_mg(self, value_g):
        if value_g is None:
            return 0.0

        return value_g * 1000.0
    # ---------------------------------------------------------
    # GUI refresh
    # ---------------------------------------------------------

    def refresh_gui(self):
        data = self.latest_data

        if not data:
            return

        temp = data.get("TEMP")
        press = data.get("PRESS")
        hum = data.get("HUM")

        uptime = data.get(
            "TIME",
            0.0,
        )
        
        if temp is not None:
            temp_f = self.c_to_f(temp)

            self.temp_label[
                "value"
            ].setText(
                f"{temp_f:.2f} °F"
            )
    

        if press is not None:
            self.press_label[
                "value"
            ].setText(
                f"{press:.2f} hPa"
            )

        if hum is not None:
            self.hum_label[
                "value"
            ].setText(
                f"{hum:.2f} %"
            )

        self.uptime_label[
            "value"
        ].setText(
            f"{uptime / 1000.0:.1f} s"
        )

        self.packet_label[
            "value"
        ].setText(
            str(
                self.stats.total_packets
            )
        )

        self.rate_label[
            "value"
        ].setText(
            f"{self.stats.packet_rate_hz:.2f} Hz"
        )

        status = data.get(
            "STATUS",
            "UNKNOWN",
        )

        self.system_status_label.setText(
            status
        )

        self.update_status_style(
            status
        )

        self.lost_packets_label.setText(
            str(
                self.stats.lost_packets
            )
        )

        self.malformed_packets_label.setText(
            str(
                self.stats.malformed_packets
            )
        )

        self.reconnects_label.setText(
            str(
                self.stats.serial_reconnects
            )
        )

        if (
            self.stats
            .min_temperature
            is not None
        ):
            self.min_temp_label.setText(
                f"{self.stats.min_temperature:.2f} °C"
            )

        if (
            self.stats
            .max_temperature
            is not None
        ):
            self.max_temp_label.setText(
                f"{self.stats.max_temperature:.2f} °C"
            )

        self.peak_accel_label.setText(
            f"{self.stats.peak_acceleration:.3f} g"
        )

        self.peak_gyro_label.setText(
            f"{self.stats.peak_gyro:.2f} °/s"
        )

        self.refresh_plots()

    def update_status_style(
        self,
        status,
    ):
        if status == "NORMAL":
            self.system_status_label.setStyleSheet(
                "font-weight: bold;"
            )

        elif status == "DEGRADED":
            self.system_status_label.setStyleSheet(
                "font-weight: bold;"
            )

        elif status == "FAULT":
            self.system_status_label.setStyleSheet(
                "font-weight: bold;"
            )

        else:
            self.system_status_label.setStyleSheet(
                ""
            )

    def refresh_plots(self):
        x = list(
            self.time_history
        )

        if not x:
            return

        self.temp_curve.setData(
            x,
            list(
                self.temp_history
            ),
        )

        self.press_curve.setData(
            x,
            list(
                self.press_history
            ),
        )

        self.hum_curve.setData(
            x,
            list(
                self.hum_history
            ),
        )

        self.ax_curve.setData(
            x,
            list(
                self.ax_history
            ),
        )

        self.ay_curve.setData(
            x,
            list(
                self.ay_history
            ),
        )

        self.az_curve.setData(
            x,
            list(
                self.az_history
            ),
        )

        self.gx_curve.setData(
            x,
            list(
                self.gx_history
            ),
        )

        self.gy_curve.setData(
            x,
            list(
                self.gy_history
            ),
        )

        self.gz_curve.setData(
            x,
            list(
                self.gz_history
            ),
        )

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------

    def toggle_logging(self):
        if self.logger.logging_enabled:
            self.logger.stop(
                stats=self.stats,
                device_info={
                    "port":
                        self.serial_manager.port,
                    "baud":
                        self.serial_manager.baud,
                },
            )

            self.logging_button.setText(
                "Start Logging"
            )

            self.add_event(
                "INFO",
                "Logging stopped",
            )

            return

        self.logger.start()

        self.logging_button.setText(
            "Stop Logging"
        )

        self.add_event(
            "INFO",
            "Logging started",
        )

    # ---------------------------------------------------------
    # Command/control
    # ---------------------------------------------------------

    def send_command(
        self,
        command,
    ):
        success = (
            self.serial_manager
            .send(command)
        )

        if success:
            self.add_event(
                "TX",
                command,
            )

            if self.logger.logging_enabled:
                self.logger.log_event(
                    "INFO",
                    "COMMAND_SENT",
                    command,
                )

        else:
            self.add_event(
                "ERROR",
                f"Unable to send: {command}",
            )

    def send_rate_command(self):
        try:
            command = (
                command_set_rate(
                    self.rate_spin.value()
                )
            )

            self.send_command(
                command
            )

        except ValueError as error:
            self.add_event(
                "ERROR",
                str(error),
            )

    # ---------------------------------------------------------
    # Events
    # ---------------------------------------------------------

    def add_event(
        self,
        level,
        message,
    ):
        timestamp = time.strftime(
            "%H:%M:%S"
        )

        self.event_log.append(
            f"[{timestamp}] "
            f"{level}: {message}"
        )

    # ---------------------------------------------------------
    # Shutdown
    # ---------------------------------------------------------

    def closeEvent(
        self,
        event,
    ):
        if self.logger.logging_enabled:
            self.logger.stop(
                stats=self.stats,
                device_info={
                    "port":
                        self.serial_manager.port,
                    "baud":
                        self.serial_manager.baud,
                },
            )

        self.serial_manager.disconnect()

        event.accept()


def run():
    app = QApplication(
        sys.argv
    )

    window = GroundStationWindow()
    window.show()

    sys.exit(
        app.exec()
    )