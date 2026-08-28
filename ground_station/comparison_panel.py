from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ground_station.database import TelemetryDatabase
from ground_station.session_analysis import compare_summaries, summarize_session


class SessionComparisonPanel(QWidget):
    def __init__(self, database_path="data/telemetry.db", parent=None):
        super().__init__(parent)
        self.database = TelemetryDatabase(database_path)

        layout = QVBoxLayout(self)

        controls = QHBoxLayout()
        self.baseline_combo = QComboBox()
        self.candidate_combo = QComboBox()
        self.refresh_button = QPushButton("Refresh Sessions")
        self.refresh_button.clicked.connect(self.refresh_sessions)
        self.compare_button = QPushButton("Compare")
        self.compare_button.clicked.connect(self.compare_selected)

        controls.addWidget(QLabel("Baseline"))
        controls.addWidget(self.baseline_combo, 1)
        controls.addWidget(QLabel("Candidate"))
        controls.addWidget(self.candidate_combo, 1)
        controls.addWidget(self.refresh_button)
        controls.addWidget(self.compare_button)
        layout.addLayout(controls)

        self.summary = QLabel("Select two sessions to compare.")
        self.summary.setStyleSheet("font-size: 15px; font-weight: 700;")
        layout.addWidget(self.summary)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(
            ["Metric", "Baseline", "Candidate", "Delta", "% change"]
        )
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        guidance = QGroupBox("How to use this")
        guidance_layout = QGridLayout(guidance)
        guidance_label = QLabel(
            "Compare a known-good session against a candidate firmware/test run. "
            "Look for changes in motion RMS, CRC failures, fault/degraded packets, "
            "temperature range, and session duration."
        )
        guidance_label.setWordWrap(True)
        guidance_layout.addWidget(guidance_label, 0, 0)
        layout.addWidget(guidance)

        self.refresh_sessions()

    def refresh_sessions(self):
        sessions = self.database.list_sessions(limit=200)
        current_base = self.baseline_combo.currentData()
        current_candidate = self.candidate_combo.currentData()

        for combo in (self.baseline_combo, self.candidate_combo):
            combo.clear()
            for session in sessions:
                label = (
                    f"#{session['id']} | {session.get('transport', '--')} | "
                    f"{session.get('firmware_version') or 'FW ?'} | "
                    f"{session.get('packet_count', 0)} packets"
                )
                combo.addItem(label, int(session["id"]))

        self._restore_selection(self.baseline_combo, current_base)
        self._restore_selection(self.candidate_combo, current_candidate)

        if len(sessions) >= 2 and current_base is None and current_candidate is None:
            self.baseline_combo.setCurrentIndex(1)
            self.candidate_combo.setCurrentIndex(0)

    @staticmethod
    def _restore_selection(combo, value):
        if value is None:
            return
        index = combo.findData(value)
        if index >= 0:
            combo.setCurrentIndex(index)

    @staticmethod
    def _format(value):
        if value is None:
            return "--"
        if isinstance(value, float):
            return f"{value:.4f}"
        return str(value)

    def compare_selected(self):
        baseline_id = self.baseline_combo.currentData()
        candidate_id = self.candidate_combo.currentData()
        if baseline_id is None or candidate_id is None:
            return

        baseline = summarize_session(
            self.database.load_session_telemetry(int(baseline_id))
        )
        candidate = summarize_session(
            self.database.load_session_telemetry(int(candidate_id))
        )
        comparison = compare_summaries(baseline, candidate)

        self.table.setRowCount(len(comparison))
        for row, (metric, values) in enumerate(comparison.items()):
            percent = values["percent_change"]
            display = [
                metric,
                self._format(values["baseline"]),
                self._format(values["candidate"]),
                self._format(values["delta"]),
                "--" if percent is None else f"{percent:+.2f} %",
            ]
            for column, value in enumerate(display):
                self.table.setItem(row, column, QTableWidgetItem(value))

        self.summary.setText(
            f"Baseline session {baseline_id} vs candidate session {candidate_id}"
        )

    def close(self):
        self.database.close()
