import math

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ground_station.flight_dynamics import FlightMotionEstimator

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
        status = "2D FLIGHT ATTITUDE" if self.valid else "NO ATTITUDE DATA"
        painter.drawText(12, 24, status)
        if self.valid:
            painter.drawText(12, 46, f"PITCH {self.pitch:+.1f}°   ROLL {self.roll:+.1f}°")


def _box_mesh(size, center=(0.0, 0.0, 0.0)):
    sx, sy, sz = (float(value) / 2.0 for value in size)
    cx, cy, cz = center
    vertices = np.array(
        [
            [cx - sx, cy - sy, cz - sz],
            [cx + sx, cy - sy, cz - sz],
            [cx + sx, cy + sy, cz - sz],
            [cx - sx, cy + sy, cz - sz],
            [cx - sx, cy - sy, cz + sz],
            [cx + sx, cy - sy, cz + sz],
            [cx + sx, cy + sy, cz + sz],
            [cx - sx, cy + sy, cz + sz],
        ],
        dtype=float,
    )
    faces = np.array(
        [
            [0, 1, 2], [0, 2, 3],
            [4, 6, 5], [4, 7, 6],
            [0, 4, 5], [0, 5, 1],
            [1, 5, 6], [1, 6, 2],
            [2, 6, 7], [2, 7, 3],
            [3, 7, 4], [3, 4, 0],
        ],
        dtype=int,
    )
    return gl.MeshData(vertexes=vertices, faces=faces)


def _circle_points(radius, center=(0.0, 0.0, 0.0), plane="xy", samples=48):
    cx, cy, cz = center
    points = []
    for index in range(samples + 1):
        angle = (2.0 * math.pi * index) / samples
        a = math.cos(angle) * radius
        b = math.sin(angle) * radius
        if plane == "yz":
            points.append([cx, cy + a, cz + b])
        elif plane == "xz":
            points.append([cx + a, cy, cz + b])
        else:
            points.append([cx + a, cy + b, cz])
    return np.array(points, dtype=float)


class GLDroneView(QWidget):
    """3D quadcopter flight visualization driven by telemetry."""

    POSITION_SCALE = 0.75
    ALTITUDE_SCALE = 0.45

    def __init__(self):
        super().__init__()
        self.view = gl.GLViewWidget()
        self.view.opts["distance"] = 14
        self.pitch = 0.0
        self.roll = 0.0
        self.position = (0.0, 0.0, 0.0)
        self._body_items = []
        self._rotation_rings = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.view)

        self._add_world_reference()
        self._add_drone()
        self.reset_camera()

    def reset_camera(self):
        self.view.setCameraPosition(distance=14, elevation=24, azimuth=42)

    def _add_world_reference(self):
        grid = gl.GLGridItem()
        grid.setSize(18, 18)
        grid.setSpacing(1, 1)
        self.view.addItem(grid)

        axis_specs = (
            ([4.5, 0.0, 0.0], (1.0, 0.25, 0.25, 0.42)),
            ([0.0, 4.5, 0.0], (0.25, 1.0, 0.35, 0.42)),
            ([0.0, 0.0, 4.5], (0.35, 0.55, 1.0, 0.42)),
        )
        for endpoint, color in axis_specs:
            axis = gl.GLLinePlotItem(
                pos=np.array([[0.0, 0.0, 0.0], endpoint], dtype=float),
                width=2,
                color=color,
                antialias=True,
            )
            self.view.addItem(axis)

        self.trail_item = gl.GLLinePlotItem(
            pos=np.array([[0.0, 0.0, 0.0]], dtype=float),
            width=3,
            color=(0.95, 0.78, 0.24, 0.82),
            antialias=True,
        )
        self.view.addItem(self.trail_item)

        self.position_marker = gl.GLScatterPlotItem(
            pos=np.array([[0.0, 0.0, 0.0]], dtype=float),
            size=8,
            color=(1.0, 0.82, 0.3, 0.85),
        )
        self.view.addItem(self.position_marker)

    def _add_mesh(self, mesh_data, color, edge_color=(0.8, 0.9, 1.0, 0.75)):
        item = gl.GLMeshItem(
            meshdata=mesh_data,
            smooth=False,
            color=color,
            shader="shaded",
            drawEdges=True,
            edgeColor=edge_color,
        )
        self.view.addItem(item)
        self._body_items.append(item)
        return item

    def _add_body_line(self, points, color, width=4):
        item = gl.GLLinePlotItem(
            pos=np.array(points, dtype=float),
            width=width,
            color=color,
            antialias=True,
        )
        self.view.addItem(item)
        self._body_items.append(item)
        return item

    def _add_drone(self):
        # Main fuselage and the companion PCB mounted above the center stack.
        self._add_mesh(
            _box_mesh((2.15, 1.55, 0.48), center=(0.0, 0.0, 0.06)),
            color=(0.14, 0.19, 0.25, 0.96),
        )
        self._add_mesh(
            _box_mesh((1.2, 0.82, 0.16), center=(0.0, 0.0, 0.42)),
            color=(0.18, 0.78, 0.48, 0.96),
            edge_color=(0.65, 1.0, 0.78, 0.9),
        )

        motors = (
            (2.55, 2.55),
            (2.55, -2.55),
            (-2.55, 2.55),
            (-2.55, -2.55),
        )
        for index, (mx, my) in enumerate(motors):
            front = mx > 0.0
            arm_color = (0.96, 0.46, 0.22, 1.0) if front else (0.45, 0.55, 0.66, 1.0)
            self._add_body_line([[0.0, 0.0, 0.0], [mx, my, 0.0]], arm_color, width=7)

            self._add_body_line(
                _circle_points(0.34, center=(mx, my, 0.08)),
                (0.78, 0.84, 0.9, 0.95),
                width=5,
            )
            prop_color = (
                (1.0, 0.45, 0.24, 0.52)
                if front
                else (0.48, 0.72, 1.0, 0.38)
            )
            self._add_body_line(
                _circle_points(0.88, center=(mx, my, 0.16)),
                prop_color,
                width=2,
            )

        # +X is the drone nose/forward direction.
        self._add_body_line(
            [[0.8, 0.0, 0.55], [2.0, 0.0, 0.55]],
            (1.0, 0.82, 0.22, 1.0),
            width=6,
        )

        body_axes = (
            ([[0, 0, 0.62], [3.45, 0, 0.62]], (1.0, 0.18, 0.18, 0.96)),
            ([[0, 0, 0.62], [0, 3.45, 0.62]], (0.15, 1.0, 0.25, 0.96)),
            ([[0, 0, 0.62], [0, 0, 3.2]], (0.2, 0.5, 1.0, 0.96)),
        )
        for points, color in body_axes:
            self._add_body_line(points, color, width=4)

        ring_specs = {
            "GX": ("yz", (1.0, 0.18, 0.18)),
            "GY": ("xz", (0.15, 1.0, 0.25)),
            "GZ": ("xy", (0.2, 0.5, 1.0)),
        }
        for key, (plane, base_color) in ring_specs.items():
            ring = self._add_body_line(
                _circle_points(1.38, center=(0.0, 0.0, 0.35), plane=plane),
                (*base_color, 0.16),
                width=2,
            )
            self._rotation_rings[key] = (ring, base_color)

        self.acceleration_vector = self._add_body_line(
            [[0.0, 0.0, 0.72], [0.0, 0.0, 0.72]],
            (1.0, 0.86, 0.25, 0.95),
            width=5,
        )

    def _apply_transform(self, valid=True):
        x, y, z = self.position
        for item in self._body_items:
            item.resetTransform()
            if valid:
                item.rotate(float(self.roll), 1, 0, 0)
                item.rotate(float(self.pitch), 0, 1, 0)
            item.translate(float(x), float(y), float(z))

    def set_attitude(self, pitch, roll, valid=True):
        self.pitch = float(pitch or 0.0)
        self.roll = float(roll or 0.0)
        self._apply_transform(valid=valid)

    def set_motion(self, motion, valid=True):
        self.position = (
            float(motion.get("forward_m", 0.0)) * self.POSITION_SCALE,
            float(motion.get("lateral_m", 0.0)) * self.POSITION_SCALE,
            float(motion.get("altitude_m", 0.0)) * self.ALTITUDE_SCALE,
        )

        trail = motion.get("trail") or [(0.0, 0.0, 0.0)]
        trail_points = np.array(
            [
                [
                    float(forward) * self.POSITION_SCALE,
                    float(lateral) * self.POSITION_SCALE,
                    float(altitude) * self.ALTITUDE_SCALE,
                ]
                for forward, lateral, altitude in trail
            ],
            dtype=float,
        )
        self.trail_item.setData(pos=trail_points)
        self.position_marker.setData(pos=np.array([self.position], dtype=float))

        vector_scale = 2.2
        end = [
            float(motion.get("dynamic_ax_g", 0.0)) * vector_scale,
            float(motion.get("dynamic_ay_g", 0.0)) * vector_scale,
            float(motion.get("dynamic_az_g", 0.0)) * vector_scale,
        ]
        self.acceleration_vector.setData(
            pos=np.array([[0.0, 0.0, 0.72], [end[0], end[1], 0.72 + end[2]]], dtype=float)
        )
        self._apply_transform(valid=valid)

    def set_angular_rates(self, gx=None, gy=None, gz=None):
        for key, value in (("GX", gx), ("GY", gy), ("GZ", gz)):
            ring, base_color = self._rotation_rings[key]
            try:
                magnitude = abs(float(value))
            except (TypeError, ValueError):
                magnitude = 0.0
            alpha = min(0.95, 0.14 + (magnitude / 55.0) * 0.81)
            ring.setData(color=(*base_color, alpha))

    def reset_motion(self):
        self.position = (0.0, 0.0, 0.0)
        self.trail_item.setData(pos=np.array([[0.0, 0.0, 0.0]], dtype=float))
        self.position_marker.setData(pos=np.array([[0.0, 0.0, 0.0]], dtype=float))
        self._apply_transform(valid=True)


class AttitudePanel(QWidget):
    """Flight View retained under the historical class name for app compatibility."""

    def __init__(self):
        super().__init__()
        self.motion_estimator = FlightMotionEstimator(trail_length=140)
        self.latest_pitch = None
        self.latest_roll = None
        self.attitude_valid = False

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        self.mode_label = QLabel()
        self.validity_label = QLabel("ATTITUDE INVALID")
        self.motion_mode_label = QLabel("POSITION: RELATIVE / ESTIMATED")
        self.motion_mode_label.setStyleSheet("font-weight: 700; color: #ffd166;")
        reset_button = QPushButton("Reset Flight Reference")
        reset_button.clicked.connect(self.reset_motion_reference)
        camera_button = QPushButton("Reset Camera")
        camera_button.clicked.connect(self.reset_camera)

        self.mode_label.setStyleSheet("font-weight: 700;")
        self.validity_label.setStyleSheet("font-weight: 700;")

        header.addWidget(self.mode_label)
        header.addWidget(self.validity_label)
        header.addWidget(self.motion_mode_label)
        header.addStretch()
        header.addWidget(reset_button)
        header.addWidget(camera_button)
        layout.addLayout(header)

        content = QHBoxLayout()
        self.view = self._create_view()
        content.addWidget(self.view, 4)
        content.addWidget(self._build_readout_panel(), 1)
        layout.addLayout(content, 1)

        note = QLabel(
            "Flight View uses the PCB as a companion telemetry module. Pitch/roll are gravity-referenced; yaw is rate-only without a magnetometer. "
            "Horizontal displacement is a short-window IMU visualization with drift damping, while vertical displacement is relative barometric altitude. "
            "These position values are diagnostic estimates, not navigation or flight-control data."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #aeb6c0;")
        layout.addWidget(note)

    def _build_readout_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 2, 2, 2)

        attitude_box = QGroupBox("Attitude / Rotation")
        attitude_grid = QGridLayout(attitude_box)
        self.pitch_label = QLabel("-- °")
        self.roll_label = QLabel("-- °")
        self.rate_labels = {key: QLabel("-- °/s") for key in ("GX", "GY", "GZ")}
        rows = (
            ("Pitch", self.pitch_label),
            ("Roll", self.roll_label),
            ("Roll rate X", self.rate_labels["GX"]),
            ("Pitch rate Y", self.rate_labels["GY"]),
            ("Yaw rate Z", self.rate_labels["GZ"]),
        )
        for row, (name, value) in enumerate(rows):
            attitude_grid.addWidget(QLabel(name), row, 0)
            value.setStyleSheet("font-size: 15px; font-weight: 700;")
            attitude_grid.addWidget(value, row, 1)
        layout.addWidget(attitude_box)

        motion_box = QGroupBox("Relative Dimensional Movement")
        motion_grid = QGridLayout(motion_box)
        self.motion_labels = {
            "forward": QLabel("0.000 m"),
            "lateral": QLabel("0.000 m"),
            "altitude": QLabel("0.000 m"),
            "vforward": QLabel("0.000 m/s"),
            "vlateral": QLabel("0.000 m/s"),
            "pressure": QLabel("-- hPa"),
        }
        motion_rows = (
            ("Forward ΔX", "forward"),
            ("Lateral ΔY", "lateral"),
            ("Baro ΔZ", "altitude"),
            ("Forward velocity", "vforward"),
            ("Lateral velocity", "vlateral"),
            ("Pressure", "pressure"),
        )
        for row, (name, key) in enumerate(motion_rows):
            motion_grid.addWidget(QLabel(name), row, 0)
            self.motion_labels[key].setStyleSheet("font-weight: 700;")
            motion_grid.addWidget(self.motion_labels[key], row, 1)
        layout.addWidget(motion_box)

        sensor_box = QGroupBox("PCB Motion Sensors")
        sensor_grid = QGridLayout(sensor_box)
        self.accel_labels = {key: QLabel("-- g") for key in ("AX", "AY", "AZ")}
        for row, key in enumerate(("AX", "AY", "AZ")):
            sensor_grid.addWidget(QLabel(key), row, 0)
            sensor_grid.addWidget(self.accel_labels[key], row, 1)
        layout.addWidget(sensor_box)
        layout.addStretch()
        return panel

    def _create_view(self):
        if OPENGL_AVAILABLE:
            try:
                view = GLDroneView()
                self.mode_label.setText("3D DRONE FLIGHT VIEW / OPENGL")
                return view
            except Exception:
                pass

        self.mode_label.setText("2D FLIGHT ATTITUDE FALLBACK")
        return ArtificialHorizon()

    def reset_camera(self):
        if hasattr(self.view, "reset_camera"):
            self.view.reset_camera()

    def reset_motion_reference(self):
        self.motion_estimator.reset()
        for key in ("forward", "lateral", "altitude"):
            self.motion_labels[key].setText("0.000 m")
        for key in ("vforward", "vlateral"):
            self.motion_labels[key].setText("0.000 m/s")
        if hasattr(self.view, "reset_motion"):
            self.view.reset_motion()

    def set_attitude(self, pitch, roll, valid=True):
        self.latest_pitch = pitch
        self.latest_roll = roll
        self.attitude_valid = bool(valid)
        self.view.set_attitude(pitch, roll, valid)
        self.validity_label.setText("ATTITUDE VALID" if valid else "ATTITUDE INVALID")
        self.validity_label.setStyleSheet(
            "font-weight: 700; color: #8ff0a4;" if valid else "font-weight: 700; color: #ff9b9b;"
        )

        if valid:
            self.pitch_label.setText(f"{float(pitch):+.1f} °")
            self.roll_label.setText(f"{float(roll):+.1f} °")
        else:
            self.pitch_label.setText("-- °")
            self.roll_label.setText("-- °")

    def set_angular_rates(self, gx=None, gy=None, gz=None):
        for key, value in (("GX", gx), ("GY", gy), ("GZ", gz)):
            label = self.rate_labels[key]
            if value is None:
                label.setText("-- °/s")
            else:
                label.setText(f"{float(value):+.2f} °/s")
        if hasattr(self.view, "set_angular_rates"):
            self.view.set_angular_rates(gx, gy, gz)

    def update_flight_data(self, telemetry, pitch=None, roll=None, valid=True):
        motion = self.motion_estimator.update(
            telemetry,
            pitch_deg=pitch if valid else 0.0,
            roll_deg=roll if valid else 0.0,
        )

        self.motion_labels["forward"].setText(f"{motion['forward_m']:+.3f} m")
        self.motion_labels["lateral"].setText(f"{motion['lateral_m']:+.3f} m")
        self.motion_labels["altitude"].setText(f"{motion['altitude_m']:+.3f} m")
        self.motion_labels["vforward"].setText(f"{motion['velocity_forward_mps']:+.3f} m/s")
        self.motion_labels["vlateral"].setText(f"{motion['velocity_lateral_mps']:+.3f} m/s")
        pressure = motion.get("pressure_hpa")
        self.motion_labels["pressure"].setText("-- hPa" if pressure is None else f"{pressure:.2f} hPa")

        for key in ("AX", "AY", "AZ"):
            value = telemetry.get(key)
            self.accel_labels[key].setText("-- g" if value is None else f"{float(value):+.3f} g")

        if hasattr(self.view, "set_motion"):
            self.view.set_motion(motion, valid=valid)
        return motion
