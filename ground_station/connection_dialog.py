from PySide6.QtCore import QSettings
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from ground_station.connection import ConnectionConfig, create_manager
from ground_station.serial_manager import SerialManager


class ConnectionDialog(QDialog):
    MODES = [
        ("USB / Serial", "serial"),
        ("Direct WiFi", "wifi"),
        ("MQTT", "mqtt"),
        ("Simulator", "demo"),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Connect to Telemetry Device")
        self.setMinimumWidth(480)
        self.settings = QSettings("EmbeddedTelemetry", "GroundStation")

        layout = QVBoxLayout(self)

        title = QLabel("CONNECTION MANAGER")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        subtitle = QLabel(
            "Choose how the ground station should communicate with the device. "
            "Your last selection is remembered locally."
        )
        subtitle.setWordWrap(True)

        layout.addWidget(title)
        layout.addWidget(subtitle)

        self.mode_combo = QComboBox()
        for label, mode in self.MODES:
            self.mode_combo.addItem(label, mode)
        self.mode_combo.currentIndexChanged.connect(self._mode_changed)
        layout.addWidget(self.mode_combo)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_serial_page())
        self.pages.addWidget(self._build_wifi_page())
        self.pages.addWidget(self._build_mqtt_page())
        self.pages.addWidget(self._build_demo_page())
        layout.addWidget(self.pages)

        buttons = QDialogButtonBox(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        buttons.button(QDialogButtonBox.Ok).setText("Use Connection")
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._restore_settings()
        self._mode_changed(self.mode_combo.currentIndex())

    def _build_serial_page(self):
        page = QWidget()
        form = QFormLayout(page)

        port_row = QHBoxLayout()
        self.serial_port_combo = QComboBox()
        refresh_button = QPushButton("Refresh")
        refresh_button.clicked.connect(self.refresh_serial_ports)
        port_row.addWidget(self.serial_port_combo, 1)
        port_row.addWidget(refresh_button)

        self.baud_combo = QComboBox()
        for baud in (9600, 19200, 38400, 57600, 115200, 230400):
            self.baud_combo.addItem(str(baud), baud)

        form.addRow("Serial port", port_row)
        form.addRow("Baud rate", self.baud_combo)
        self.refresh_serial_ports()
        return page

    def _build_wifi_page(self):
        page = QWidget()
        form = QFormLayout(page)

        self.wifi_host = QLineEdit()
        self.wifi_host.setPlaceholderText("192.168.1.50")
        self.wifi_port = QSpinBox()
        self.wifi_port.setRange(1, 65535)
        self.wifi_port.setValue(9000)

        form.addRow("Device IP / host", self.wifi_host)
        form.addRow("TCP port", self.wifi_port)
        return page

    def _build_mqtt_page(self):
        page = QWidget()
        form = QFormLayout(page)

        self.mqtt_host = QLineEdit()
        self.mqtt_host.setPlaceholderText("192.168.1.10")
        self.mqtt_port = QSpinBox()
        self.mqtt_port.setRange(1, 65535)
        self.mqtt_port.setValue(1883)
        self.device_id = QLineEdit("esp8285-node")
        self.mqtt_user = QLineEdit()
        self.mqtt_password = QLineEdit()
        self.mqtt_password.setEchoMode(QLineEdit.Password)

        form.addRow("Broker IP / host", self.mqtt_host)
        form.addRow("Broker port", self.mqtt_port)
        form.addRow("Device ID", self.device_id)
        form.addRow("Username", self.mqtt_user)
        form.addRow("Password", self.mqtt_password)
        return page

    @staticmethod
    def _build_demo_page():
        page = QWidget()
        layout = QVBoxLayout(page)
        message = QLabel(
            "Runs the hardware-free ESP8285 simulator. It uses the same telemetry, "
            "commands, CRC checks, fault injection, and state transitions as the real device."
        )
        message.setWordWrap(True)
        layout.addWidget(message)
        layout.addStretch()
        return page

    def refresh_serial_ports(self):
        previous = self.serial_port_combo.currentData() if hasattr(self, "serial_port_combo") else None
        if hasattr(self, "serial_port_combo"):
            self.serial_port_combo.clear()

        for port in SerialManager.available_ports():
            label = f"{port['device']} - {port['description']}"
            self.serial_port_combo.addItem(label, port["device"])

        if self.serial_port_combo.count() == 0:
            self.serial_port_combo.addItem("COM3", "COM3")

        target = previous or self.settings.value("serial_port", "COM3")
        for index in range(self.serial_port_combo.count()):
            if self.serial_port_combo.itemData(index) == target:
                self.serial_port_combo.setCurrentIndex(index)
                break

    def selected_config(self):
        return ConnectionConfig(
            mode=self.mode_combo.currentData(),
            serial_port=self.serial_port_combo.currentData() or "COM3",
            baud=int(self.baud_combo.currentData() or 115200),
            host=(self.wifi_host.text() if self.mode_combo.currentData() == "wifi" else self.mqtt_host.text()).strip(),
            tcp_port=self.wifi_port.value(),
            mqtt_port=self.mqtt_port.value(),
            device_id=self.device_id.text().strip() or "esp8285-node",
            mqtt_user=self.mqtt_user.text().strip() or None,
            mqtt_password=self.mqtt_password.text() or None,
        )

    def build_manager(self):
        return create_manager(self.selected_config())

    def _validate_and_accept(self):
        try:
            create_manager(self.selected_config())
        except ValueError as error:
            QMessageBox.warning(self, "Connection Settings", str(error))
            return

        self._save_settings()
        self.accept()

    def _mode_changed(self, index):
        self.pages.setCurrentIndex(index)

    def _restore_settings(self):
        mode = self.settings.value("mode", "serial")
        for index in range(self.mode_combo.count()):
            if self.mode_combo.itemData(index) == mode:
                self.mode_combo.setCurrentIndex(index)
                break

        baud = int(self.settings.value("baud", 115200))
        baud_index = self.baud_combo.findData(baud)
        if baud_index >= 0:
            self.baud_combo.setCurrentIndex(baud_index)

        self.wifi_host.setText(self.settings.value("wifi_host", ""))
        self.wifi_port.setValue(int(self.settings.value("wifi_port", 9000)))
        self.mqtt_host.setText(self.settings.value("mqtt_host", ""))
        self.mqtt_port.setValue(int(self.settings.value("mqtt_port", 1883)))
        self.device_id.setText(self.settings.value("device_id", "esp8285-node"))
        self.mqtt_user.setText(self.settings.value("mqtt_user", ""))

    def _save_settings(self):
        config = self.selected_config()
        self.settings.setValue("mode", config.mode)
        self.settings.setValue("serial_port", config.serial_port)
        self.settings.setValue("baud", config.baud)
        self.settings.setValue("wifi_host", self.wifi_host.text().strip())
        self.settings.setValue("wifi_port", self.wifi_port.value())
        self.settings.setValue("mqtt_host", self.mqtt_host.text().strip())
        self.settings.setValue("mqtt_port", self.mqtt_port.value())
        self.settings.setValue("device_id", self.device_id.text().strip())
        self.settings.setValue("mqtt_user", self.mqtt_user.text().strip())
