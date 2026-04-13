from __future__ import annotations

import math

import numpy as np
import pyqtgraph.opengl as gl
from PyQt6.QtGui import QColor

from .._data.data_frame import DoAFrame
from ..constants import VFO_COLORS


def _hex_to_rgba(hex_color: str, alpha: float = 1.0) -> tuple[float, float, float, float]:
    c = QColor(hex_color)
    return (c.redF(), c.greenF(), c.blueF(), alpha)


class Spatial3DWidget(gl.GLViewWidget):
    """3D visualization of antenna array geometry and bearing cones.

    Shows:
    - Antenna element positions (from settings: UCA, ULA, or custom)
    - Ground plane grid
    - Bearing cones/wedges per active VFO (direction + confidence)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackgroundColor("#1e1e1e")
        self.setCameraPosition(distance=5, elevation=30, azimuth=45)

        # Ground plane grid
        grid = gl.GLGridItem()
        grid.setSize(4, 4, 1)
        grid.setSpacing(0.5, 0.5, 1)
        grid.setColor((80, 80, 80, 100))
        self.addItem(grid)

        # Antenna element scatter
        self._antenna_scatter = gl.GLScatterPlotItem(
            pos=np.zeros((1, 3), dtype=np.float32),
            color=(0.2, 0.8, 1.0, 1.0),
            size=12,
            pxMode=True,
        )
        self.addItem(self._antenna_scatter)

        # Lines connecting antenna elements
        self._antenna_lines = gl.GLLinePlotItem(
            pos=np.zeros((2, 3), dtype=np.float32),
            color=(0.3, 0.6, 0.8, 0.5),
            width=2,
            mode="line_strip",
        )
        self.addItem(self._antenna_lines)

        # Bearing cone items per VFO: {(source_id, vfo_index): GLLinePlotItem}
        self._bearing_items: dict[tuple[str, int], gl.GLLinePlotItem] = {}

        # Default UCA with 5 elements
        self._update_antenna_positions("UCA", 5, 0.5)

    def update_settings(self, settings: dict):
        """Update antenna array geometry from settings."""
        ant_type = settings.get("ant_arrangement", "UCA")
        spacing = float(settings.get("ant_spacing_meters", 0.5))
        n_elements = int(settings.get("num_ant_elements", 5))

        custom_x = settings.get("custom_array_x_meters", "")
        custom_y = settings.get("custom_array_y_meters", "")

        if ant_type == "Custom" and custom_x and custom_y:
            try:
                x = [float(v) for v in str(custom_x).split(",")]
                y = [float(v) for v in str(custom_y).split(",")]
                positions = np.zeros((len(x), 3), dtype=np.float32)
                positions[:, 0] = x
                positions[:, 1] = y
                self._set_antenna_positions(positions)
            except (ValueError, IndexError):
                self._update_antenna_positions(ant_type, n_elements, spacing)
        else:
            self._update_antenna_positions(ant_type, n_elements, spacing)

    def _update_antenna_positions(self, ant_type: str, n_elements: int, spacing: float):
        """Compute antenna element positions for standard array types."""
        if ant_type == "UCA":
            # Uniform Circular Array
            to_r = 1.0 / (math.sqrt(2.0) * math.sqrt(1.0 - math.cos(2.0 * math.pi / n_elements)))
            r = spacing * to_r
            angles = np.linspace(0, 2 * np.pi, n_elements, endpoint=False)
            positions = np.zeros((n_elements, 3), dtype=np.float32)
            positions[:, 0] = r * np.cos(angles)
            positions[:, 1] = r * np.sin(angles)
        elif ant_type == "ULA":
            # Uniform Linear Array
            positions = np.zeros((n_elements, 3), dtype=np.float32)
            positions[:, 1] = np.arange(n_elements) * spacing - (n_elements - 1) * spacing / 2
        else:
            # Default to UCA
            self._update_antenna_positions("UCA", n_elements, spacing)
            return

        self._set_antenna_positions(positions)

    def _set_antenna_positions(self, positions: np.ndarray):
        """Set the antenna element positions in 3D space."""
        # Lift elements slightly above ground
        pos = positions.copy()
        pos[:, 2] = 0.05

        self._antenna_scatter.setData(pos=pos)

        # Close the loop for line strip
        loop = np.vstack([pos, pos[0:1]])
        self._antenna_lines.setData(pos=loop)

    def on_frame(self, frame: DoAFrame):
        """Update bearing cone for the given VFO."""
        key = (frame.source_id, frame.vfo_index)

        if key not in self._bearing_items:
            color = _hex_to_rgba(VFO_COLORS[frame.vfo_index % len(VFO_COLORS)], alpha=0.7)
            item = gl.GLLinePlotItem(
                pos=np.zeros((2, 3), dtype=np.float32),
                color=color,
                width=3,
                mode="lines",
            )
            self.addItem(item)
            self._bearing_items[key] = item

        # Draw a bearing line from center outward
        bearing_rad = np.deg2rad(90.0 - frame.bearing_deg)  # Convert compass to math angle
        length = 2.0  # Length of bearing line

        # Main bearing line
        center = np.array([0, 0, 0.1], dtype=np.float32)
        end = np.array(
            [length * np.cos(bearing_rad), length * np.sin(bearing_rad), 0.1],
            dtype=np.float32,
        )

        # Confidence-based cone width (wider = less confident)
        half_width = max(5.0, 30.0 * (1.0 - frame.confidence))
        left_rad = np.deg2rad(90.0 - frame.bearing_deg + half_width)
        right_rad = np.deg2rad(90.0 - frame.bearing_deg - half_width)
        left_end = np.array(
            [length * 0.8 * np.cos(left_rad), length * 0.8 * np.sin(left_rad), 0.1],
            dtype=np.float32,
        )
        right_end = np.array(
            [length * 0.8 * np.cos(right_rad), length * 0.8 * np.sin(right_rad), 0.1],
            dtype=np.float32,
        )

        # Lines: center->end, center->left, center->right
        lines = np.array(
            [center, end, center, left_end, center, right_end],
            dtype=np.float32,
        )
        self._bearing_items[key].setData(pos=lines)

    def remove_source(self, source_id: str):
        """Remove all bearing items for a source."""
        keys_to_remove = [k for k in self._bearing_items if k[0] == source_id]
        for key in keys_to_remove:
            item = self._bearing_items.pop(key)
            self.removeItem(item)
