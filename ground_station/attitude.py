from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QHBoxLayout, QLabel, QVBoxLayout, QWidget

try:
    import numpy as np
    import pyqtgraph.opengl as gl

    OPENGL_AVAILABLE = True
except Exception:
    np = None
    gl = None
    OPENGL_AVAILABLE = False


class ArtificialHorizon(QWidget):
    def __init__(self):
        super().__init__()
        self.pitch = 0.0
        self.roll = 0.0
        self.valid = False
        self.setMinimumSize(420, 300)

    def set_attitude(self, pitch, roll, valid=True):
        self.pitch = float(pitch or 0.0)
        self.roll = float(roll or 0.0)
        self.valid = bool(valid)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        center_x = width / 2.0
        center_y = height / 2.0

        painter.fillRect(self.rect(), QColor("#161616"))

        painter.save()
        painter.translate(center_x, center_y)
        painter.rotate(-self.roll)

        pitch_offset = self.pitch * 3.0
        painter.translate(0, pitch_offset)

        span = max(width, height) * 2
        painter.fillRect(
            int(-span),
            int(-span),
            int(span * 2),
            int(span),
            QBrush(QColor("#24425f")),
        )
        painter.fillRect(
            int(-span),
            0,
            int(span * 2),
            int(span),
            QBrush(QColor("#5a3f27")),
        )

        horizon_pen = QPen(QColor("#f2f2f2"))
        horizon_pen.setWidth(3)
        painter.setPen(horizon_pen)
        painter.drawLine(int(-span), 0, int(span), 0)

        tick_pen = QPen(QColor("#d7d7d7"))
        tick_pen.setWidth(1)
        painter.setPen(tick_pen)
        for degrees in range(-30, 31, 10):
            if degrees == 0:
                continue
            y = -degrees * 3
            half = 45 if degrees % 20 == 0 else 28
            painter.drawLine(-half, y, half, y)

        painter.restore()

        aircraft_pen = QPen(QColor("#f4d35e"))
        aircraft_pen.setWidth(4)
        painter.setPen(aircraft_pen)
        painter.drawLine(int(center_x - 70), int(center_y), int(center_x - 15), int(center_y))
        painter.drawLine(int(center_x + 15), int(center_y), int(center_x + 70), int(center_y))
        painter.drawLine(int(center_x), int(center_y - 8), int(center_x), int(center_y + 18))

        painter.setPen(QColor("#f0f0f0"))
        status = "2D FALLBACK" if self.valid else "NO ATTITUDE DATA"
        painter.drawText(12, 24, status)


class GLBoardView(QWidget):
    def __init__(self):
        super().__init__()
        self.view = gl.GLViewWidget()
        self.view.opts["distance"] = 9

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        grid = gl.GLGridItem()
        grid.scale(1, 1, 1)
        self.view.addItem(grid)

        board_points = np.array(
            [
                [-2.2, -1.2, 0.0],
                [2.2, -1.2, 0.0],
                [2.2, 1.2, 0.0],
                [-2.2, 1.2, 0.0],
                [-2.2, -1.2, 0.0],
                [2.2, 1.2, 0.0],
                [2.2, -1.2, 0.0],
                [-2.2, 1.2, 0.0],
            ],
            dtype=float,
        )

        self.board = gl.GLLinePlotItem(
            pos=board_points,
            width=3,
            antialias=True,
            mode="line_strip",
        )
        self.view.addItem(self.board)

        x_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [3, 0, 0]], dtype=float),
            width=2,
        )
        y_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, 3, 0]], dtype=float),
            width=2,
        )
        z_axis = gl.GLLinePlotItem(
            pos=np.array([[0, 0, 0], [0, 0, 3]], dtype=float),
            width=2,
        )
        self.view.addItem(x_axis)
        self.view.addItem(y_axis)
        self.view.addItem(z_axis)

    def set_attitude(self, pitch, roll, valid=True):
        self.board.resetTransform()
        if valid:
            self.board.rotate(float(roll or 0.0), 1, 0, 0)
            self.board.rotate(float(pitch or 0.0), 0, 1, 0)


class AttitudePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.mode_label = QLabel("3D OPENGL" if OPENGL_AVAILABLE else "2D FALLBACK")
        self.pitch_label = QLabel("Pitch: -- °")
        self.roll_label = QLabel("Roll: -- °")

        header.addWidget(self.mode_label)
        header.addStretch()
        header.addWidget(self.pitch_label)
        header.addWidget(self.roll_label)
        layout.addLayout(header)

        self.view = GLBoardView() if OPENGL_AVAILABLE else ArtificialHorizon()
        layout.addWidget(self.view, 1)

    def set_attitude(self, pitch, roll, valid=True):
        self.view.set_attitude(pitch, roll, valid)

        if valid:
            self.pitch_label.setText(f"Pitch: {pitch:.1f} °")
            self.roll_label.setText(f"Roll: {roll:.1f} °")
        else:
            self.pitch_label.setText("Pitch: -- °")
            self.roll_label.setText("Roll: -- °")
