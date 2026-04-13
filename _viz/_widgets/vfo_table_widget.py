from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QHeaderView,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from .._data.data_frame import DoAFrame
from ..constants import VFO_COLORS


class VfoTableWidget(QWidget):
    """Summary table showing per-VFO DoA results: frequency, bearing, power, confidence, status."""

    COLUMNS = ["VFO", "Freq (MHz)", "Bearing", "Power (dB)", "Confidence", "Status"]

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, len(self.COLUMNS))
        self._table.setHorizontalHeaderLabels(self.COLUMNS)
        self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self._table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)

        # Style
        self._table.setStyleSheet("""
            QTableWidget {
                background-color: #1e1e1e;
                color: #cccccc;
                gridline-color: #444444;
                alternate-background-color: #252525;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #cccccc;
                padding: 4px;
                border: 1px solid #444444;
            }
            """)

        layout.addWidget(self._table)

        # Track latest frame per (source, vfo_index) for table rows
        self._row_keys: list[tuple[str, int]] = []
        self._frame_data: dict[tuple[str, int], DoAFrame] = {}

    def on_frame(self, frame: DoAFrame):
        """Update the table with a new DoA frame."""
        key = (frame.source_id, frame.vfo_index)
        self._frame_data[key] = frame

        if key not in self._row_keys:
            self._row_keys.append(key)

        self._rebuild_table()

    def remove_source(self, source_id: str):
        """Remove all rows for a source."""
        self._row_keys = [(sid, vi) for sid, vi in self._row_keys if sid != source_id]
        self._frame_data = {k: v for k, v in self._frame_data.items() if k[0] != source_id}
        self._rebuild_table()

    def _rebuild_table(self):
        self._table.setRowCount(len(self._row_keys))
        for row, key in enumerate(self._row_keys):
            frame = self._frame_data.get(key)
            if frame is None:
                continue

            source_id, vfo_idx = key
            color = QColor(VFO_COLORS[vfo_idx % len(VFO_COLORS)])

            # VFO label with color
            vfo_item = QTableWidgetItem(f"VFO-{vfo_idx}")
            vfo_item.setForeground(color)
            self._table.setItem(row, 0, vfo_item)

            # Frequency
            freq_mhz = frame.frequency_hz / 1e6
            self._table.setItem(row, 1, self._make_item(f"{freq_mhz:.3f}"))

            # Bearing
            self._table.setItem(row, 2, self._make_item(f"{frame.bearing_deg:.1f}\u00b0"))

            # Power
            self._table.setItem(row, 3, self._make_item(f"{frame.power_dbm:.1f}"))

            # Confidence
            conf_pct = frame.confidence * 100
            self._table.setItem(row, 4, self._make_item(f"{conf_pct:.0f}%"))

            # Status (source kind)
            self._table.setItem(row, 5, self._make_item(frame.source_kind.value))

    def _make_item(self, text: str) -> QTableWidgetItem:
        item = QTableWidgetItem(text)
        item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        return item
