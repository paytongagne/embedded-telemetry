import csv
import math
from pathlib import Path

import pyqtgraph as pg
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ground_station.database import TelemetryDatabase


class HistoryPanel(QWidget):
    """Browse, replay, and export persisted telemetry sessions."""

    def __init__(self, database_path="data/telemetry.db", parent=None):
        super().__init__(parent)
        self.database = TelemetryDatabase(database_path)
        self.current_session_id = None
        self.current_rows = []
        self.replay_position = 0.0

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.refresh_button = QPushButton("Refresh Sessions")
        self.refresh_button.clicked.connect(self.refresh_sessions)
        self.load_button = QPushButton("Load Session")
        self.load_button.clicked.connect(self.load_selected_session)
        self.replay_button = QPushButton("Replay")
        self.replay_button.clicked.connect(self.start_replay)
        self.stop_button = QPushButton("Stop Replay")
        self.stop_button.clicked.connect(self.stop_replay)
        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_selected_session)

        self.speed_combo = QComboBox()
        for speed in (0.5, 1.0, 2.0, 5.0, 10.0):
            self.speed_combo.addItem(f"{speed:g}x", speed)
        self.speed_combo.setCurrentIndex(1)

        controls.addWidget(self.refresh_button)
        controls.addWidget(self.load_button)
        controls.addWidget(QLabel("Replay speed"))
        controls.addWidget(self.speed_combo)
        controls.addWidget(self.replay_button)
        controls.addWidget(self.stop_button)
        controls.addWidget(self.export_button)
        controls.addStretch()
        layout.addLayout(controls)

        self.session_table = QTableWidget(0, 7)
        self.session_table.setHorizontalHeaderLabels(
            ["ID", "Started", "Transport", "Endpoint", "Firmware", "Packets", "Ended"]
        )
        self.session_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.session_table.setSelectionMode(QTableWidget.SingleSelection)
        self.session_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.session_table.doubleClicked.connect(self.load_selected_session)
        self.session_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.session_table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.session_table, 1)

        self.summary_label = QLabel("Select a recorded session.")
        self.summary_label.setStyleSheet("font-weight: 700;")
        layout.addWidget(self.summary_label)

        self.temp_plot = pg.PlotWidget(title="Historical Temperature")
        self.temp_plot.setLabel("bottom", "Device uptime", units="s")
        self.temp_plot.setLabel("left", "Temperature", units="°F")
        self.temp_plot.showGrid(x=True, y=True, alpha=0.2)
        self.temp_curve = self.temp_plot.plot()

        self.motion_plot = pg.PlotWidget(title="Historical Acceleration Magnitude")
        self.motion_plot.setLabel("bottom", "Device uptime", units="s")
        self.motion_plot.setLabel("left", "Acceleration magnitude", units="g")
        self.motion_plot.showGrid(x=True, y=True, alpha=0.2)
        self.motion_curve = self.motion_plot.plot()

        layout.addWidget(self.temp_plot, 1)
        layout.addWidget(self.motion_plot, 1)

        self.event_log = QPlainTextEdit()
        self.event_log.setReadOnly(True)
        self.event_log.setPlaceholderText("Session events will appear here.")
        layout.addWidget(self.event_log, 1)

        self.replay_timer = QTimer(self)
        self.replay_timer.setInterval(100)
        self.replay_timer.timeout.connect(self._replay_tick)

        self.refresh_sessions()

    @staticmethod
    def _display_time(value):
        if not value:
            return "--"
        return str(value).replace("T", " ")[:19] + "Z"

    @staticmethod
    def _c_to_f(value):
        if value is None:
            return float("nan")
        return (float(value) * 9.0 / 5.0) + 32.0

    @staticmethod
    def _accel_magnitude(row):
        values = (row.get("ax_g"), row.get("ay_g"), row.get("az_g"))
        if any(value is None for value in values):
            return float("nan")
        return math.sqrt(sum(float(value) ** 2 for value in values))

    def refresh_sessions(self):
        sessions = self.database.list_sessions(limit=200)
        self.session_table.setRowCount(len(sessions))
        for row_index, session in enumerate(sessions):
            values = [
                session["id"],
                self._display_time(session.get("started_at_utc")),
                session.get("transport") or "--",
                session.get("endpoint") or "--",
                session.get("firmware_version") or "--",
                session.get("packet_count") or 0,
                self._display_time(session.get("ended_at_utc")),
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(str(value))
                if column == 0:
                    item.setData(Qt.UserRole, int(session["id"]))
                self.session_table.setItem(row_index, column, item)

        if sessions and self.session_table.currentRow() < 0:
            self.session_table.selectRow(0)

    def _selected_session_id(self):
        row = self.session_table.currentRow()
        if row < 0:
            return None
        item = self.session_table.item(row, 0)
        return None if item is None else int(item.data(Qt.UserRole) or item.text())

    def load_selected_session(self):
        session_id = self._selected_session_id()
        if session_id is None:
            return

        self.stop_replay()
        self.current_session_id = session_id
        self.current_rows = self.database.load_session_telemetry(session_id)
        events = self.database.load_session_events(session_id)
        self._render_rows(self.current_rows)

        self.event_log.clear()
        for event in events:
            timestamp = self._display_time(event.get("recorded_at_utc"))
            self.event_log.appendPlainText(
                f"{timestamp}  {event.get('level', 'INFO'):<8} "
                f"{event.get('category', '')}: {event.get('message', '')}"
            )

        if self.current_rows:
            first = self.current_rows[0]
            last = self.current_rows[-1]
            duration_ms = (last.get("device_time_ms") or 0) - (first.get("device_time_ms") or 0)
            self.summary_label.setText(
                f"Session {session_id} | {len(self.current_rows)} packets | "
                f"{max(0, duration_ms) / 1000.0:.1f} s recorded device time"
            )
        else:
            self.summary_label.setText(f"Session {session_id} contains no telemetry packets.")

    def _render_rows(self, rows):
        x = []
        temp = []
        motion = []
        for index, row in enumerate(rows):
            device_time = row.get("device_time_ms")
            x.append(index if device_time is None else float(device_time) / 1000.0)
            temp.append(self._c_to_f(row.get("temperature_c")))
            motion.append(self._accel_magnitude(row))
        self.temp_curve.setData(x, temp)
        self.motion_curve.setData(x, motion)

    def start_replay(self):
        if not self.current_rows:
            self.load_selected_session()
        if not self.current_rows:
            return
        self.replay_position = 0.0
        self.temp_curve.setData([], [])
        self.motion_curve.setData([], [])
        self.replay_timer.start()
        self.summary_label.setText(f"Replaying session {self.current_session_id}...")

    def stop_replay(self):
        self.replay_timer.stop()

    def _replay_tick(self):
        if not self.current_rows:
            self.stop_replay()
            return

        speed = float(self.speed_combo.currentData() or 1.0)
        self.replay_position += speed
        count = max(1, min(len(self.current_rows), int(self.replay_position)))
        self._render_rows(self.current_rows[:count])

        if count >= len(self.current_rows):
            self.stop_replay()
            self.summary_label.setText(
                f"Replay complete | session {self.current_session_id} | "
                f"{len(self.current_rows)} packets"
            )

    def export_selected_session(self):
        session_id = self._selected_session_id()
        if session_id is None:
            return

        rows = self.database.load_session_telemetry(session_id)
        if not rows:
            self.summary_label.setText(f"Session {session_id} has no telemetry to export.")
            return

        output_dir = Path("exports")
        output_dir.mkdir(parents=True, exist_ok=True)
        path = output_dir / f"telemetry_session_{session_id}.csv"

        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
            writer.writeheader()
            writer.writerows(rows)

        self.summary_label.setText(f"Exported session {session_id} to {path}")

    def close(self):
        self.stop_replay()
        self.database.close()
