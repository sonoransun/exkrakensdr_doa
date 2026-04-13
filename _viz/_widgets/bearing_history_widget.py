from __future__ import annotations

import time
from collections import defaultdict

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QColor

from .._data.data_frame import DoAFrame
from ..constants import VFO_COLORS

HISTORY_WINDOW_SEC = 120  # 2-minute rolling window
MAX_POINTS = 600  # Max data points per VFO in history


class BearingHistoryWidget(pg.PlotWidget):
    """Rolling chart of bearing vs. time for all VFOs.

    Displays bearing history over a configurable time window (default 120s).
    Each VFO gets a distinct color matching VFO_COLORS.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground("#1e1e1e")
        self.setTitle("Bearing History", color="w", size="11pt")
        self.setLabel("left", "Bearing", units="\u00b0")
        self.setLabel("bottom", "Time (s ago)")
        self.showGrid(x=True, y=True, alpha=0.3)
        self.setYRange(0, 360)
        self.setXRange(-HISTORY_WINDOW_SEC, 0)

        # Per-source, per-VFO histories: {source_id: {vfo_index: (times[], bearings[])}}
        self._histories: dict[str, dict[int, tuple[list[float], list[float]]]] = defaultdict(dict)
        self._curves: dict[str, dict[int, pg.PlotDataItem]] = defaultdict(dict)
        self._start_time = time.time()

    def on_frame(self, frame: DoAFrame):
        """Append a bearing measurement to the history."""
        source_id = frame.source_id
        vfo_idx = frame.vfo_index
        now = time.time()
        t = now - self._start_time

        if vfo_idx not in self._histories[source_id]:
            self._histories[source_id][vfo_idx] = ([], [])
            color = QColor(VFO_COLORS[vfo_idx % len(VFO_COLORS)])
            curve = self.plot([], [], pen=pg.mkPen(color, width=2), symbol="o", symbolSize=3, symbolBrush=color)
            self._curves[source_id][vfo_idx] = curve

        times, bearings = self._histories[source_id][vfo_idx]
        times.append(t)
        bearings.append(frame.bearing_deg)

        # Trim old data
        cutoff = t - HISTORY_WINDOW_SEC
        while times and times[0] < cutoff:
            times.pop(0)
            bearings.pop(0)

        # Also limit total points
        if len(times) > MAX_POINTS:
            times[:] = times[-MAX_POINTS:]
            bearings[:] = bearings[-MAX_POINTS:]

        # Update plot data (time relative to now, so it scrolls)
        t_rel = np.array(times) - now + self._start_time
        t_display = t_rel - t_rel[-1] if len(t_rel) > 0 else t_rel
        self._curves[source_id][vfo_idx].setData(t_display, np.array(bearings))

    def remove_source(self, source_id: str):
        if source_id in self._curves:
            for vfo_idx, curve in self._curves[source_id].items():
                self.removeItem(curve)
            del self._curves[source_id]
        self._histories.pop(source_id, None)
