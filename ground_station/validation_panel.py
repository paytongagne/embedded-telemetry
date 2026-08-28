from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ground_station.validation import FaultValidationEngine


class ValidationPanel(QWidget):
    def __init__(self, send_command, state_getter, connected_getter, parent=None):
        super().__init__(parent)
        self.send_command = send_command
        self.state_getter = state_getter
        self.connected_getter = connected_getter
        self.engine = FaultValidationEngine()

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.start_button = QPushButton("Run Fault-Recovery Validation")
        self.start_button.clicked.connect(self.start_validation)
        self.stop_button = QPushButton("Stop")
        self.stop_button.clicked.connect(self.stop_validation)
        self.status_label = QLabel("IDLE")
        self.status_label.setStyleSheet("font-size: 16px; font-weight: 700;")

        header.addWidget(self.start_button)
        header.addWidget(self.stop_button)
        header.addWidget(self.status_label)
        header.addStretch()
        layout.addLayout(header)

        description = QLabel(
            "Automates NORMAL → DEGRADED → NORMAL → DEGRADED → FAULT → NORMAL "
            "using the firmware's safe fault-injection commands. Each state transition "
            "must be observed before its timeout."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Test step", "Status", "Elapsed", "Detail"])
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)

        self.timer = QTimer(self)
        self.timer.setInterval(150)
        self.timer.timeout.connect(self._tick)
        self._refresh()

    def start_validation(self):
        if not self.connected_getter():
            self.status_label.setText("CONNECT DEVICE FIRST")
            return

        self.engine.start()
        self.status_label.setText("RUNNING")
        self.timer.start()
        self._send_pending_action()
        self._refresh()

    def stop_validation(self):
        self.engine.stop()
        self.timer.stop()
        self.status_label.setText("STOPPED")
        self._refresh()

    def _tick(self):
        self.engine.tick(
            state=self.state_getter(),
            connected=self.connected_getter(),
        )
        self._send_pending_action()
        self._refresh()

        if self.engine.finished:
            self.timer.stop()
            self.status_label.setText("PASS" if self.engine.passed else "FAIL")

    def _send_pending_action(self):
        action = self.engine.next_action()
        if action:
            self.send_command(action)

    def _refresh(self):
        results = self.engine.results
        self.table.setRowCount(len(results))
        for row, result in enumerate(results):
            elapsed = "--" if result.elapsed_seconds is None else f"{result.elapsed_seconds:.2f} s"
            values = (result.name, result.status, elapsed, result.detail)
            for column, value in enumerate(values):
                self.table.setItem(row, column, QTableWidgetItem(str(value)))
