from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont, QPen

from .._data.data_frame import DoAFrame
from ..constants import DOA_ARRAY_SIZE, VFO_COLORS


class DoACompassWidget(pg.PlotWidget):
    """Polar compass plot showing DoA results for multiple VFOs and sources.

    Each VFO gets a filled DoA curve and a peak bearing line.
    Multi-source overlay uses different line styles per source.
    """

    # Line styles for different source kinds (solid, dash, dot, dash-dot)
    SOURCE_STYLES = [Qt.PenStyle.SolidLine, Qt.PenStyle.DashLine, Qt.PenStyle.DotLine, Qt.PenStyle.DashDotLine]

    def __init__(self, compass_offset: float = 0.0, parent=None):
        super().__init__(parent)
        self._compass_offset = compass_offset

        self.setAspectLocked(True)
        self.setBackground("#1e1e1e")
        self.hideAxis("bottom")
        self.hideAxis("left")
        self.setMouseEnabled(x=False, y=False)
        self.setMenuEnabled(False)
        self.setTitle("DoA Compass", color="w", size="12pt")

        # Draw compass grid
        self._draw_compass_grid()

        # VFO curve items: {source_id: {vfo_index: (curve, peak_line)}}
        self._plot_items: dict[str, dict[int, tuple[pg.PlotDataItem, pg.PlotDataItem]]] = {}
        self._source_style_idx: dict[str, int] = {}
        self._next_style = 0

    def set_compass_offset(self, offset: float):
        self._compass_offset = offset

    def on_frame(self, frame: DoAFrame):
        """Update the compass with a new DoA frame."""
        source_id = frame.source_id
        vfo_idx = frame.vfo_index

        # Assign a style index to new sources
        if source_id not in self._source_style_idx:
            self._source_style_idx[source_id] = self._next_style
            self._next_style = (self._next_style + 1) % len(self.SOURCE_STYLES)

        if source_id not in self._plot_items:
            self._plot_items[source_id] = {}

        # Create plot items for this VFO if needed
        if vfo_idx not in self._plot_items[source_id]:
            self._plot_items[source_id][vfo_idx] = self._create_vfo_items(source_id, vfo_idx)

        curve, peak_line = self._plot_items[source_id][vfo_idx]

        # Convert DoA array to compass polar coordinates
        # The DoA array is indexed 0-359 degrees
        # Compass: 0=North (up), clockwise, with compass_offset applied
        thetas_deg = np.arange(DOA_ARRAY_SIZE, dtype=np.float64)
        compass_thetas = (90.0 - thetas_deg + self._compass_offset) % 360.0
        compass_thetas_rad = np.deg2rad(compass_thetas)

        # Scale amplitudes to radius (shift so min is near center)
        amps = frame.doa_array.astype(np.float64)
        amps = amps - np.min(amps)
        max_amp = np.max(amps)
        if max_amp > 0:
            amps = amps / max_amp
        radius = 0.15 + amps * 0.85  # inner radius 0.15, outer radius 1.0

        # Convert polar to cartesian for the plot
        x = radius * np.cos(compass_thetas_rad)
        y = radius * np.sin(compass_thetas_rad)

        # Close the curve
        x = np.append(x, x[0])
        y = np.append(y, y[0])

        curve.setData(x, y)

        # Peak bearing line from center to edge
        peak_compass = (90.0 - frame.bearing_deg + self._compass_offset) % 360.0
        peak_rad = np.deg2rad(peak_compass)
        peak_x = [0, 1.05 * np.cos(peak_rad)]
        peak_y = [0, 1.05 * np.sin(peak_rad)]
        peak_line.setData(peak_x, peak_y)

    def remove_source(self, source_id: str):
        """Remove all plot items for a source."""
        if source_id in self._plot_items:
            for vfo_idx, (curve, peak) in self._plot_items[source_id].items():
                self.removeItem(curve)
                self.removeItem(peak)
            del self._plot_items[source_id]

    def _create_vfo_items(self, source_id: str, vfo_idx: int):
        color = QColor(VFO_COLORS[vfo_idx % len(VFO_COLORS)])
        style_idx = self._source_style_idx.get(source_id, 0)
        pen_style = self.SOURCE_STYLES[style_idx % len(self.SOURCE_STYLES)]

        # DoA curve
        pen = QPen(color, 2)
        pen.setStyle(pen_style)
        fill_color = QColor(color)
        fill_color.setAlpha(40)
        curve = self.plot([], [], pen=pen, fillLevel=0, fillBrush=fill_color)

        # Peak bearing line
        peak_pen = QPen(color, 2)
        peak_pen.setStyle(pen_style)
        peak_line = self.plot([], [], pen=peak_pen, symbol="o", symbolSize=6, symbolBrush=color)

        return curve, peak_line

    def _draw_compass_grid(self):
        """Draw concentric circles and cardinal direction labels."""
        # Concentric circles
        for r in [0.25, 0.5, 0.75, 1.0]:
            theta = np.linspace(0, 2 * np.pi, 100)
            x = r * np.cos(theta)
            y = r * np.sin(theta)
            self.plot(x, y, pen=pg.mkPen("#444444", width=1))

        # Cross lines (N-S, E-W)
        for angle in [0, 90, 180, 270]:
            rad = np.deg2rad(angle)
            x = [0, 1.15 * np.cos(rad)]
            y = [0, 1.15 * np.sin(rad)]
            self.plot(x, y, pen=pg.mkPen("#555555", width=1))

        # Cardinal labels
        label_r = 1.22
        labels = {"N": 90, "E": 0, "S": 270, "W": 180}
        for text, angle_deg in labels.items():
            rad = np.deg2rad(angle_deg)
            item = pg.TextItem(text, color="#aaaaaa", anchor=(0.5, 0.5))
            item.setFont(QFont("Arial", 12, QFont.Weight.Bold))
            item.setPos(label_r * np.cos(rad), label_r * np.sin(rad))
            self.addItem(item)

        # Set fixed range
        self.setXRange(-1.4, 1.4, padding=0)
        self.setYRange(-1.4, 1.4, padding=0)
