import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QLabel, QVBoxLayout, QWidget

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
        self.setMinimumSize(520, 360)

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
        radius = min(width, height) * 0.43

        painter.fillRect(self.rect(), QColor("#101318"))

        painter.save()
        painter.translate(center_x, center_y)
        painter.setClipRect(int(-radius), int(-radius), int(radius * 2), int(radius * 2))
        painter.rotate(-self.roll)

        pitch_scale = max(3.0, radius / 30.0)
        painter.translate(0, self.pitch * pitch_scale)
        span = max(width, height) * 2

        painter.fillRect(
            int(-span), int(-span), int(span * 2), int(span), QBrush(QColor("#20496b"))
        )
        painter.fillRect(
            int(-span), 0, int(span * 2), int(span), QBrush(QColor("#65472d"))
        )

        horizon_pen = QPen(QColor("#f2f2f2"))
        horizon_pen.setWidth(3)
        painter.setPen(horizon_pen)
        painter.drawLine(int(-span), 0, int(span), 0)

        tick_pen = QPen(QColor("#d9e0e8"))
        tick_pen.setWidth(1)
        painter.setPen(tick_pen)
        for degrees in range(-40, 41, 5):
            if degrees == 0:
                continue
            y = int(-degrees * pitch_scale)
            major = degrees % 10 == 0
            half = 56 if major else 30
            painter.drawLine(-half, y, half, y)
            if major:
                painter.drawText(-half - 32, y + 5, str(abs(degrees)))
                painter.drawText(half + 8, y + 5, str(abs(degrees)))

        painter.restore()

        ring_pen = QPen(QColor("#687482"))
        ring_pen.setWidth(2)
        painter.setPen(ring_pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(
            int(center_x - radius), int(center_y - radius), int(radius * 2), int(radius * 2)
        )

        # Bank-angle ticks around the top of the instrument.
        painter.setPen(QPen(QColor("#d8dee6"), 2))
        for angle in (-60, -45, -30, -20, -10, 0, 10, 20, 30, 45, 60):
            radians = math.radians(angle - 90)
            outer_x = center_x + math.cos(radians) * radius
            outer_y = center_y + math.sin(radians) * radius
            inner = radius - (15 if angle % 30 == 0 else 9)
            inner_x = center_x + math.cos(radians) * inner
            inner_y = center_y + math.sin(radians) * inner
            painter.drawLine(int(inner_x), int(inner_y), int(outer_x), int(outer_y))

        aircraft_pen = QPen(QColor("#ffd166"))
        aircraft_pen.setWidth(5)
        painter.setPen(aircraft_pen)
        painter.drawLine(int(center_x - 82), int(center_y), int(center_x - 18), int(center_y))
        painter.drawLine(int(center_x + 18), int(center_y), int(center_x + 82), int(center_y))
        painter.drawLine(int(center_x), int(center_y - 10), int(center_x), int(center_y + 22))

        painter.setPen(QColor("#f0f0f0"))
        status = "2D ATTITUDE" if self.valid else "NO ATTITUDE DATA"
        painter.drawText(12, 24, status)
        if self.valid:
            painter.drawText(12, 46, f"PITCH {self.pitch:+.1f}°   ROLL {self.roll:+.1f}°")


class GLAircraftView(QWidget):
    def __init__(self):
        super().__init__()
        self.view = gl.GLViewWidget()
        self.view.opts["distance"] = 12
        self.view.setCameraPosition(distance=12, elevation=24, azimuth=38)
        self._body_items = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self._add_world_reference()
        self._add_aircraft()

    def _add_world_reference(self):
        grid = gl.GLGridItem()
        grid.setSize(14, 14)
        grid.setSpacing(1, 1)
        self.view.addItem(grid)

        # Fixed world axes provide a stable reference while the aircraft rotates.
        axis_specs = (
            ([4.2, 0.0, 0.0], (1.0, 0.25, 0.25, 0.75)),
            ([0.0, 4.2, 0.0], (0.25, 1.0, 0.35, 0.75)),
            ([0.0, 0.0, 4.2], (0.35, 0.55, 1.0, 0.75)),
        )
        for endpoint, color in axis_specs:
            axis = gl.GLLinePlotItem(
                pos=np.array([[0.0, 0.0, 0.0], endpoint], dtype=float),
                width=2,
                color=color,
                antialias=True,
            )
            self.view.addItem(axis)

    def _add_aircraft(self):
        # A recognizable low-poly aircraft: nose points +X, wings span Y, vertical is Z.
        vertices = np.array(
            [
                [3.0, 0.0, 0.0],      # 0 nose
                [1.2, -0.34, 0.18],    # 1 fuselage front
                [1.2, 0.34, 0.18],     # 2
                [1.2, -0.34, -0.18],   # 3
                [1.2, 0.34, -0.18],    # 4
                [-2.5, -0.25, 0.14],   # 5 tail body
                [-2.5, 0.25, 0.14],    # 6
                [-2.5, -0.25, -0.14],  # 7
                [-2.5, 0.25, -0.14],   # 8
                [0.35, -3.0, 0.0],     # 9 left wing tip
                [0.35, 3.0, 0.0],      # 10 right wing tip
                [-2.2, -1.35, 0.0],    # 11 left tailplane
                [-2.2, 1.35, 0.0],     # 12 right tailplane
                [-2.15, 0.0, 1.15],    # 13 vertical tail
            ],
            dtype=float,
        )

        faces = np.array(
            [
                [0, 1, 2], [0, 3, 1], [0, 4, 3], [0, 2, 4],
                [1, 5, 6], [1, 6, 2], [3, 7, 5], [3, 5, 1],
                [4, 8, 7], [4, 7, 3], [2, 6, 8], [2, 8, 4],
                [5, 7, 8], [5, 8, 6],
                [1, 9, 5], [2, 6, 10], [1, 2, 10], [1, 10, 9],
                [5, 11, 6], [6, 11, 12],
                [5, 13, 6],
            ],
            dtype=int,
        )

        mesh_data = gl.MeshData(vertexes=vertices, faces=faces)
        aircraft = gl.GLMeshItem(
            meshdata=mesh_data,
            smooth=False,
            color=(0.22, 0.66, 0.95, 0.82),
            shader="shaded",
            drawEdges=True,
            edgeColor=(0.85, 0.93, 1.0, 0.8),
        )
        self.view.addItem(aircraft)
        self._body_items.append(aircraft)

        # Body-fixed axes rotate with the aircraft and make rotation direction obvious.
        body_axes = (
            ([[0, 0, 0], [3.8, 0, 0]], (1.0, 0.18, 0.18, 1.0)),
            ([[0, 0, 0], [0, 3.8, 0]], (0.15, 1.0, 0.25, 1.0)),
            ([[0, 0, 0], [0, 0, 3.0]], (0.2, 0.5, 1.0, 1.0)),
        )
        for points, color in body_axes:
            item = gl.GLLinePlotItem(
                pos=np.array(points, dtype=float),
                width=4,
                color=color,
                antialias=True,
            )
            self.view.addItem(item)
            self._body_items.append(item)

    def set_attitude(self, pitch, roll, valid=True):
        for item in self._body_items:
            item.resetTransform()
            if valid:
                # Body X is forward, Y is right/wing axis, Z is up.
                item.rotate(float(roll or 0.0), 1, 0, 0)
                item.rotate(float(pitch or 0.0), 0, 1, 0)


class AttitudePanel(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.mode_label = QLabel()
        self.pitch_label = QLabel("Pitch: -- °")
        self.roll_label = QLabel("Roll: -- °")
        self.validity_label = QLabel("ATTITUDE INVALID")

        self.mode_label.setStyleSheet("font-weight: 700;")
        self.pitch_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.roll_label.setStyleSheet("font-size: 15px; font-weight: 700;")
        self.validity_label.setStyleSheet("font-weight: 700;")

        header.addWidget(self.mode_label)
        header.addWidget(self.validity_label)
        header.addStretch()
        header.addWidget(self.pitch_label)
        header.addWidget(self.roll_label)
        layout.addLayout(header)

        self.view = self._create_view()
        layout.addWidget(self.view, 1)

        rate_box = QWidget()
        rate_grid = QGridLayout(rate_box)
        rate_grid.setContentsMargins(4, 2, 4, 2)
        self.rate_labels = {}
        definitions = (
            ("GX", "Roll rate / X", "°/s"),
            ("GY", "Pitch rate / Y", "°/s"),
            ("GZ", "Yaw rate / Z", "°/s"),
        )
        for column, (key, title, unit) in enumerate(definitions):
            title_label = QLabel(title)
            title_label.setAlignment(Qt.AlignCenter)
            value_label = QLabel(f"-- {unit}")
            value_label.setAlignment(Qt.AlignCenter)
            value_label.setStyleSheet("font-size: 16px; font-weight: 700;")
            rate_grid.addWidget(title_label, 0, column)
            rate_grid.addWidget(value_label, 1, column)
            self.rate_labels[key] = value_label
        layout.addWidget(rate_box)

        note = QLabel(
            "Red/green/blue axes are aircraft X/Y/Z. The faint grid and fixed axes remain in the world frame. "
            "Yaw rate is visible from GZ, but absolute yaw/heading is intentionally not displayed because this sensor set has no magnetometer reference."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #aeb6c0;")
        layout.addWidget(note)

    def _create_view(self):
        if OPENGL_AVAILABLE:
            try:
                view = GLAircraftView()
                self.mode_label.setText("3D AIRCRAFT / OPENGL")
                return view
            except Exception:
                pass

        self.mode_label.setText("2D ARTIFICIAL HORIZON")
        return ArtificialHorizon()

    def set_attitude(self, pitch, roll, valid=True):
        self.view.set_attitude(pitch, roll, valid)
        self.validity_label.setText("ATTITUDE VALID" if valid else "ATTITUDE INVALID")
        self.validity_label.setStyleSheet(
            "font-weight: 700; color: #8ff0a4;" if valid else "font-weight: 700; color: #ff9b9b;"
        )

        if valid:
            self.pitch_label.setText(f"Pitch: {pitch:+.1f} °")
            self.roll_label.setText(f"Roll: {roll:+.1f} °")
        else:
            self.pitch_label.setText("Pitch: -- °")
            self.roll_label.setText("Roll: -- °")

    def set_angular_rates(self, gx=None, gy=None, gz=None):
        for key, value in (("GX", gx), ("GY", gy), ("GZ", gz)):
            label = self.rate_labels[key]
            if value is None:
                label.setText("-- °/s")
            else:
                label.setText(f"{float(value):+.2f} °/s")
