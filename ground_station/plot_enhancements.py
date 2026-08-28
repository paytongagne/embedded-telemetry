import math
from collections import deque

import pyqtgraph as pg
from PySide6.QtCore import Qt


class DashboardPlotEnhancer:
    """Improves readability and inspection of the live dashboard plots."""

    def __init__(self, window, max_points=180):
        self.window = window
        self.max_points = max_points
        self.time_history = deque(maxlen=max_points)
        self.accel_magnitude_history = deque(maxlen=max_points)
        self.gyro_magnitude_history = deque(maxlen=max_points)
        self.crosshair_lines = {}
        self.crosshair_labels = {}
        self._scene_connections = []

        pg.setConfigOptions(antialias=True)
        self._style_curves()
        self._add_magnitude_curves()
        self._add_threshold_guides()
        self._link_time_axes()
        self._install_crosshairs()

    def _style_curves(self):
        # Consistent axis colors make X/Y/Z motion immediately distinguishable.
        self.window.temp_curve.setPen(pg.mkPen("#ffb454", width=2.2))
        self.window.press_curve.setPen(pg.mkPen("#69d2e7", width=2.2))
        self.window.hum_curve.setPen(pg.mkPen("#c792ea", width=2.2))

        axis_pens = {
            "ax_curve": "#ff6464",
            "ay_curve": "#69db7c",
            "az_curve": "#4dabf7",
            "gx_curve": "#ff6464",
            "gy_curve": "#69db7c",
            "gz_curve": "#4dabf7",
        }
        for attribute, color in axis_pens.items():
            curve = getattr(self.window, attribute)
            curve.setPen(pg.mkPen(color, width=1.8))
            curve.setDownsampling(auto=True, method="peak")
            curve.setClipToView(True)

        for curve in (
            self.window.temp_curve,
            self.window.press_curve,
            self.window.hum_curve,
        ):
            curve.setDownsampling(auto=True, method="peak")
            curve.setClipToView(True)

        for plot in self._plots():
            plot.showGrid(x=True, y=True, alpha=0.28)
            plot.getPlotItem().setMenuEnabled(True)
            plot.setMouseEnabled(x=True, y=True)
            legend = plot.getPlotItem().legend
            if legend is not None:
                legend.setBrush(pg.mkBrush(18, 22, 28, 210))
                legend.setPen(pg.mkPen(90, 100, 112, 180))

    def _add_magnitude_curves(self):
        self.accel_magnitude_curve = self.window.accel_plot.plot(
            name="|A|",
            pen=pg.mkPen("#ffd166", width=2.6),
        )
        self.gyro_magnitude_curve = self.window.gyro_plot.plot(
            name="|ω|",
            pen=pg.mkPen("#ffd166", width=2.6),
        )

    def _add_threshold_guides(self):
        guides = (
            (self.window.temp_plot, 95.0, "High temp 95°F"),
            (self.window.hum_plot, 15.0, "Low humidity 15%"),
        )
        for plot, value, label in guides:
            line = pg.InfiniteLine(
                pos=value,
                angle=0,
                movable=False,
                pen=pg.mkPen("#ff8f70", width=1.4, style=Qt.DashLine),
                label=label,
                labelOpts={"position": 0.96, "color": "#ffb09b"},
            )
            plot.addItem(line)

    def _link_time_axes(self):
        reference = self.window.temp_plot
        for plot in self._plots()[1:]:
            plot.setXLink(reference)

    def _install_crosshairs(self):
        for plot in self._plots():
            vertical = pg.InfiniteLine(
                angle=90,
                movable=False,
                pen=pg.mkPen("#b9c2cc", width=1, style=Qt.DotLine),
            )
            label = pg.TextItem(
                text="",
                anchor=(0, 1),
                fill=pg.mkBrush(16, 19, 24, 220),
                border=pg.mkPen(100, 112, 126, 180),
                color="#e8edf2",
            )
            vertical.hide()
            label.hide()
            plot.addItem(vertical, ignoreBounds=True)
            plot.addItem(label, ignoreBounds=True)
            self.crosshair_lines[plot] = vertical
            self.crosshair_labels[plot] = label

            callback = lambda pos, source=plot: self._mouse_moved(source, pos)
            plot.scene().sigMouseMoved.connect(callback)
            self._scene_connections.append((plot.scene().sigMouseMoved, callback))

    def _mouse_moved(self, source_plot, scene_position):
        if not source_plot.sceneBoundingRect().contains(scene_position):
            return

        point = source_plot.getPlotItem().vb.mapSceneToView(scene_position)
        x_value = point.x()
        y_value = point.y()

        for plot, line in self.crosshair_lines.items():
            line.setPos(x_value)
            line.show()
            label = self.crosshair_labels[plot]
            if plot is source_plot:
                label.setText(f"t={x_value:.2f} s\ny={y_value:.3f}")
                label.setPos(x_value, y_value)
                label.show()
            else:
                label.hide()

    def update(self, telemetry):
        device_time = telemetry.get("TIME")
        if device_time is None:
            return

        self.time_history.append(float(device_time) / 1000.0)
        self.accel_magnitude_history.append(
            self._magnitude(telemetry.get("AX"), telemetry.get("AY"), telemetry.get("AZ"))
        )
        self.gyro_magnitude_history.append(
            self._magnitude(telemetry.get("GX"), telemetry.get("GY"), telemetry.get("GZ"))
        )

        x_values = list(self.time_history)
        self.accel_magnitude_curve.setData(x_values, list(self.accel_magnitude_history))
        self.gyro_magnitude_curve.setData(x_values, list(self.gyro_magnitude_history))

    @staticmethod
    def _magnitude(x, y, z):
        if None in (x, y, z):
            return float("nan")
        return math.sqrt(float(x) ** 2 + float(y) ** 2 + float(z) ** 2)

    def _plots(self):
        return [
            self.window.temp_plot,
            self.window.press_plot,
            self.window.hum_plot,
            self.window.accel_plot,
            self.window.gyro_plot,
        ]
