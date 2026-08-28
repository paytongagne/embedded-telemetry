from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class EngineeringPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        metrics_box = QGroupBox("Derived Engineering Metrics")
        grid = QGridLayout(metrics_box)

        definitions = (
            ("accel_magnitude_g", "Acceleration magnitude", "g"),
            ("gyro_magnitude_dps", "Angular-rate magnitude", "°/s"),
            ("accel_rms_g", "Rolling accel RMS", "g"),
            ("gyro_rms_dps", "Rolling gyro RMS", "°/s"),
            ("accel_std_g", "Acceleration variability", "g"),
            ("gyro_std_dps", "Gyro variability", "°/s"),
            ("temperature_delta_c", "Window temperature delta", "°C"),
            ("window_samples", "Analysis window", "samples"),
        )

        self.metric_labels = {}
        for index, (key, title, unit) in enumerate(definitions):
            row = index // 2
            column = (index % 2) * 2
            grid.addWidget(QLabel(title), row, column)
            value = QLabel("--")
            value.setStyleSheet("font-size: 16px; font-weight: 700;")
            grid.addWidget(value, row, column + 1)
            self.metric_labels[key] = (value, unit)

        layout.addWidget(metrics_box)

        thresholds = QGroupBox("Default Alert Thresholds")
        threshold_layout = QGridLayout(thresholds)
        values = (
            ("Temperature", "> 35 °C"),
            ("Humidity", "< 15 %"),
            ("Rolling acceleration RMS", "> 1.35 g"),
            ("Rolling gyro RMS", "> 40 °/s"),
            ("Packet loss", "> 2 %"),
        )
        for row, (name, value) in enumerate(values):
            threshold_layout.addWidget(QLabel(name), row, 0)
            threshold_layout.addWidget(QLabel(value), row, 1)
        layout.addWidget(thresholds)

        alert_box = QGroupBox("Active Alerts / Alert History")
        alert_layout = QVBoxLayout(alert_box)
        self.alert_log = QPlainTextEdit()
        self.alert_log.setReadOnly(True)
        self.alert_log.setPlaceholderText("No engineering alerts.")
        alert_layout.addWidget(self.alert_log)
        layout.addWidget(alert_box, 1)

        self.active_label = QLabel("ACTIVE ALERTS: 0")
        self.active_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(self.active_label)

    def update_metrics(self, metrics):
        for key, (label, unit) in self.metric_labels.items():
            value = metrics.get(key)
            if value is None:
                label.setText("--")
            elif key == "window_samples":
                label.setText(f"{int(value)} {unit}")
            else:
                label.setText(f"{float(value):.3f} {unit}")

    def apply_alert_result(self, result):
        for alert in result.get("raised", []):
            value = "" if alert.value is None else f" value={alert.value}"
            threshold = "" if alert.threshold is None else f" threshold={alert.threshold}"
            self.alert_log.appendPlainText(
                f"RAISED {alert.severity:<8} {alert.key}: {alert.message}{value}{threshold}"
            )

        for alert in result.get("cleared", []):
            self.alert_log.appendPlainText(
                f"CLEARED {alert.severity:<8} {alert.key}: {alert.message}"
            )

        active = result.get("active", [])
        self.active_label.setText(f"ACTIVE ALERTS: {len(active)}")
