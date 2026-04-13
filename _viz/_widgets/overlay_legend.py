from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPen
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ..constants import SourceKind

# Visual style for each source kind
SOURCE_STYLE_MAP = {
    SourceKind.LIVE_WS: {"label": "Live", "dash": Qt.PenStyle.SolidLine, "color": "#00ff66"},
    SourceKind.FILE_CSV: {"label": "CSV", "dash": Qt.PenStyle.DashLine, "color": "#ffaa00"},
    SourceKind.FILE_IQ: {"label": "IQ", "dash": Qt.PenStyle.DashLine, "color": "#ff6600"},
    SourceKind.FILE_WAV: {"label": "WAV", "dash": Qt.PenStyle.DashLine, "color": "#6699ff"},
    SourceKind.SYNTHETIC: {"label": "Synth", "dash": Qt.PenStyle.DotLine, "color": "#ff66ff"},
}


class LineStyleSwatch(QWidget):
    """Small widget that draws a horizontal line with a specific style."""

    def __init__(self, color: str, pen_style: Qt.PenStyle, parent=None):
        super().__init__(parent)
        self._color = QColor(color)
        self._pen_style = pen_style
        self.setFixedSize(40, 16)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(self._color, 2)
        pen.setStyle(self._pen_style)
        painter.setPen(pen)
        painter.drawLine(2, 8, 38, 8)
        painter.end()


class OverlayLegend(QWidget):
    """Legend showing the visual style for each source kind."""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(12)

        for kind, style in SOURCE_STYLE_MAP.items():
            entry = QHBoxLayout()
            entry.setSpacing(4)

            swatch = LineStyleSwatch(style["color"], style["dash"])
            entry.addWidget(swatch)

            label = QLabel(style["label"])
            label.setStyleSheet(f"color: {style['color']}; font-size: 11px;")
            entry.addWidget(label)

            layout.addLayout(entry)

        layout.addStretch()
