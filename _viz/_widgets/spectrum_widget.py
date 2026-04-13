from __future__ import annotations

import numpy as np
import pyqtgraph as pg
from PyQt6.QtGui import QColor

from .._data.data_frame import DoAFrame, SpectrumFrame
from ..constants import WATERFALL_COLORMAP, WATERFALL_HISTORY_ROWS


def _build_waterfall_lut() -> pg.ColorMap:
    """Build a pyqtgraph ColorMap from the SDR# waterfall colorscale."""
    positions = [p for p, _ in WATERFALL_COLORMAP]
    colors = [QColor(c) for _, c in WATERFALL_COLORMAP]
    rgba = [(c.red(), c.green(), c.blue(), 255) for c in colors]
    return pg.ColorMap(positions, rgba)


class SpectrumWidget(pg.GraphicsLayoutWidget):
    """Combined spectrum line plot and waterfall heatmap.

    Accepts DoAFrame (with spectrum data) or SpectrumFrame.
    Spectrum data is optional in DoAFrame; if absent, the widget is not updated.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setBackground("#1e1e1e")

        # --- Spectrum plot (top) ---
        self._spectrum_plot = self.addPlot(row=0, col=0)
        self._spectrum_plot.setLabel("left", "Power", units="dB")
        self._spectrum_plot.setLabel("bottom", "Frequency", units="Hz")
        self._spectrum_plot.showGrid(x=True, y=True, alpha=0.3)
        self._spectrum_plot.setYRange(-90, 0)

        # Spectrum traces per source
        self._spectrum_traces: dict[str, pg.PlotDataItem] = {}
        self._source_colors: dict[str, str] = {}
        self._next_color_idx = 0
        self._trace_colors = ["#00ccff", "#ff6600", "#00ff66", "#ff66ff", "#ffff00"]

        # --- Waterfall (bottom) ---
        self._waterfall_plot = self.addPlot(row=1, col=0)
        self._waterfall_plot.setLabel("left", "Time")
        self._waterfall_plot.setLabel("bottom", "Frequency", units="Hz")
        self._waterfall_plot.hideAxis("left")

        self._waterfall_img = pg.ImageItem()
        self._waterfall_plot.addItem(self._waterfall_img)

        # Waterfall data buffer
        self._wf_data = np.full((WATERFALL_HISTORY_ROWS, 1024), -80.0, dtype=np.float32)
        self._wf_freq_range = (0.0, 1.0)

        # Color map
        cmap = _build_waterfall_lut()
        lut = cmap.getLookupTable(nPts=256)
        self._waterfall_img.setLookupTable(lut)

        # Link X axes
        self._waterfall_plot.setXLink(self._spectrum_plot)

    def on_frame(self, frame: DoAFrame):
        """Update spectrum and waterfall from a DoAFrame with spectrum data."""
        if frame.spectrum_freqs is None or frame.spectrum_power_db is None:
            return
        self._update_spectrum(frame.source_id, frame.spectrum_freqs, frame.spectrum_power_db)
        self._update_waterfall(frame.spectrum_freqs, frame.spectrum_power_db)

    def on_spectrum_frame(self, frame: SpectrumFrame):
        """Update from a standalone SpectrumFrame."""
        self._update_spectrum(frame.source_id, frame.freq_axis_hz, frame.power_db)
        self._update_waterfall(frame.freq_axis_hz, frame.power_db)

    def remove_source(self, source_id: str):
        trace = self._spectrum_traces.pop(source_id, None)
        if trace:
            self._spectrum_plot.removeItem(trace)

    def _update_spectrum(self, source_id: str, freqs: np.ndarray, power_db: np.ndarray):
        if source_id not in self._spectrum_traces:
            color = self._trace_colors[self._next_color_idx % len(self._trace_colors)]
            self._next_color_idx += 1
            self._source_colors[source_id] = color
            trace = self._spectrum_plot.plot([], [], pen=pg.mkPen(color, width=1))
            self._spectrum_traces[source_id] = trace

        self._spectrum_traces[source_id].setData(freqs, power_db)

    def _update_waterfall(self, freqs: np.ndarray, power_db: np.ndarray):
        n_bins = len(power_db)
        if n_bins == 0:
            return

        # Resize waterfall buffer if bin count changed
        if self._wf_data.shape[1] != n_bins:
            self._wf_data = np.full((WATERFALL_HISTORY_ROWS, n_bins), -80.0, dtype=np.float32)

        # Scroll: shift rows down, insert new at top
        self._wf_data = np.roll(self._wf_data, 1, axis=0)
        self._wf_data[0, :] = power_db

        # Normalize for colormap: map [-90, 0] to [0, 1]
        display = np.clip((self._wf_data + 90.0) / 90.0, 0, 1)

        # Set image data and position
        freq_min, freq_max = float(freqs[0]), float(freqs[-1])
        self._waterfall_img.setImage(display.T, autoLevels=False, levels=[0, 1])
        self._waterfall_img.setRect(freq_min, 0, freq_max - freq_min, WATERFALL_HISTORY_ROWS)
