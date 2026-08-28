import sys

from PySide6.QtWidgets import QApplication

from ground_station.alerts import AlertEngine
from ground_station.app import GroundStationWindow
from ground_station.comparison_panel import SessionComparisonPanel
from ground_station.engineering import EngineeringMetrics
from ground_station.engineering_panel import EngineeringPanel
from ground_station.fault_capture import FaultBlackBox
from ground_station.history_panel import HistoryPanel
from ground_station.parser import parse_telemetry
from ground_station.plot_enhancements import DashboardPlotEnhancer
from ground_station.validation_panel import ValidationPanel


class GroundStationV2Window(GroundStationWindow):
    def __init__(self, serial_manager=None):
        self.engineering_metrics = EngineeringMetrics(window_size=50)
        self.alert_engine = AlertEngine()
        self.fault_black_box = FaultBlackBox(pre_samples=60, post_samples=20)
        self.engineering_panel = None
        self.history_panel = None
        self.comparison_panel = None
        self.validation_panel = None
        self.plot_enhancer = None
        super().__init__(serial_manager=serial_manager)
        self.plot_enhancer = DashboardPlotEnhancer(self, max_points=180)

    def build_ui(self):
        super().build_ui()
        tabs = self.centralWidget()

        self.engineering_panel = EngineeringPanel()
        self.history_panel = HistoryPanel()
        self.comparison_panel = SessionComparisonPanel()
        self.validation_panel = ValidationPanel(
            send_command=self.send_command,
            state_getter=lambda: self.latest_data.get(
                "STATUS", self.latest_data.get("STATE", "UNKNOWN")
            ),
            connected_getter=lambda: bool(self.serial_manager.connected),
            metadata_getter=self.validation_metadata,
        )

        tabs.insertTab(1, self.engineering_panel, "Engineering")
        tabs.insertTab(2, self.history_panel, "History / Replay")
        tabs.insertTab(3, self.comparison_panel, "Compare")
        tabs.insertTab(4, self.validation_panel, "Validation")

    def on_serial_line(self, line):
        telemetry = parse_telemetry(line)
        super().on_serial_line(line)

        if telemetry is None:
            return

        if self.plot_enhancer is not None:
            self.plot_enhancer.update(telemetry)

        self.attitude_panel.set_angular_rates(
            telemetry.get("GX"),
            telemetry.get("GY"),
            telemetry.get("GZ"),
        )

        metrics = self.engineering_metrics.update(telemetry)
        alert_result = self.alert_engine.evaluate(
            telemetry,
            metrics,
            packet_loss_percent=self.stats.packet_loss_percent,
        )

        self.engineering_panel.update_metrics(metrics)
        self.engineering_panel.apply_alert_result(alert_result)

        for alert in alert_result.get("raised", []):
            message = f"{alert.key}: {alert.message}"
            self.add_event(alert.severity, message)
            self._record_v2_event(alert.severity, "ALERT", message)

        for alert in alert_result.get("cleared", []):
            message = f"{alert.key}: cleared"
            self.add_event("INFO", message)
            self._record_v2_event("INFO", "ALERT_CLEAR", message)

        capture_path = self.fault_black_box.update(
            telemetry,
            metadata=self.validation_metadata(),
        )
        if capture_path is not None:
            message = f"Fault black-box capture saved: {capture_path}"
            self.add_event("INFO", message)
            self._record_v2_event("INFO", "FAULT_CAPTURE", message)

    def validation_metadata(self):
        metadata = {
            "firmware": self.latest_data.get("FW", "unknown"),
            "system_state": self.latest_data.get(
                "STATUS", self.latest_data.get("STATE", "UNKNOWN")
            ),
            "packets_observed": self.stats.total_packets,
            "packet_loss_percent": f"{self.stats.packet_loss_percent:.3f}",
            "connection": getattr(self.serial_manager, "port", "unknown"),
        }
        session_id = getattr(self.serial_manager, "session_id", None)
        if session_id is not None:
            metadata["session_id"] = session_id
        return metadata

    def _record_v2_event(self, level, category, message):
        database = getattr(self.serial_manager, "database", None)
        session_id = getattr(self.serial_manager, "session_id", None)
        if database is not None and session_id is not None:
            database.log_event(session_id, level, category, message)

    def closeEvent(self, event):
        if self.history_panel is not None:
            self.history_panel.close()
        if self.comparison_panel is not None:
            self.comparison_panel.close()
        super().closeEvent(event)


def run_v2(serial_manager=None):
    app = QApplication(sys.argv)
    window = GroundStationV2Window(serial_manager=serial_manager)
    window.show()
    sys.exit(app.exec())
