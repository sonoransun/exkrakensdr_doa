from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QWidget,
)

from .._data.source_manager import SourceManager

SPEED_OPTIONS = ["0.25x", "0.5x", "1x", "2x", "4x", "Max"]


class TimelineWidget(QWidget):
    """VCR transport bar with play/pause/stop, seek slider, and speed control.

    Operates on all seekable sources via the SourceManager.
    """

    def __init__(self, source_manager: SourceManager, parent=None):
        super().__init__(parent)
        self._source_manager = source_manager

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)

        # Play/Pause
        self._play_btn = QPushButton("\u25b6")
        self._play_btn.setFixedWidth(36)
        self._play_btn.setToolTip("Play / Pause")
        self._play_btn.clicked.connect(self._toggle_play_pause)
        layout.addWidget(self._play_btn)

        # Stop
        self._stop_btn = QPushButton("\u25a0")
        self._stop_btn.setFixedWidth(36)
        self._stop_btn.setToolTip("Stop")
        self._stop_btn.clicked.connect(self._stop)
        layout.addWidget(self._stop_btn)

        # Position label
        self._pos_label = QLabel("0:00")
        self._pos_label.setFixedWidth(50)
        layout.addWidget(self._pos_label)

        # Seek slider
        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setRange(0, 1000)
        self._slider.setValue(0)
        self._slider.sliderMoved.connect(self._on_seek)
        layout.addWidget(self._slider, stretch=1)

        # Duration label
        self._dur_label = QLabel("0:00")
        self._dur_label.setFixedWidth(50)
        layout.addWidget(self._dur_label)

        # Speed selector
        self._speed_combo = QComboBox()
        self._speed_combo.addItems(SPEED_OPTIONS)
        self._speed_combo.setCurrentText("1x")
        self._speed_combo.currentTextChanged.connect(self._on_speed_change)
        layout.addWidget(self._speed_combo)

        self._playing = False

        # Style
        self.setStyleSheet("""
            QPushButton { color: #cccccc; background-color: #2d2d2d; border: 1px solid #555; border-radius: 4px; padding: 4px; }
            QPushButton:hover { background-color: #444; }
            QLabel { color: #cccccc; }
            QComboBox { color: #cccccc; background-color: #2d2d2d; border: 1px solid #555; padding: 2px; }
            """)

    def on_progress(self, position: float):
        """Update slider position from source progress (0.0-1.0)."""
        self._slider.blockSignals(True)
        self._slider.setValue(int(position * 1000))
        self._slider.blockSignals(True)

        # Update time label (estimate from position and duration)
        duration_ms = self._get_total_duration_ms()
        if duration_ms and duration_ms > 0:
            current_sec = int(position * duration_ms / 1000)
            total_sec = int(duration_ms / 1000)
            self._pos_label.setText(f"{current_sec // 60}:{current_sec % 60:02d}")
            self._dur_label.setText(f"{total_sec // 60}:{total_sec % 60:02d}")
        self._slider.blockSignals(False)

    def _toggle_play_pause(self):
        self._playing = not self._playing
        for sid in self._source_manager.source_ids:
            source = self._source_manager.get_source(sid)
            if source and source.is_seekable:
                if self._playing:
                    source.start_source()
                else:
                    source.pause_source()
        self._play_btn.setText("\u23f8" if self._playing else "\u25b6")

    def _stop(self):
        self._playing = False
        self._play_btn.setText("\u25b6")
        for sid in self._source_manager.source_ids:
            source = self._source_manager.get_source(sid)
            if source and source.is_seekable:
                source.stop_source()
        self._slider.setValue(0)
        self._pos_label.setText("0:00")

    def _on_seek(self, value: int):
        position = value / 1000.0
        for sid in self._source_manager.source_ids:
            source = self._source_manager.get_source(sid)
            if source and source.is_seekable:
                source.seek(position)

    def _on_speed_change(self, text: str):
        if text == "Max":
            speed = 0.0
        else:
            speed = float(text.replace("x", ""))
        for sid in self._source_manager.source_ids:
            source = self._source_manager.get_source(sid)
            if source and source.is_seekable:
                source.set_playback_speed(speed)

    def _get_total_duration_ms(self) -> int | None:
        for sid in self._source_manager.source_ids:
            source = self._source_manager.get_source(sid)
            if source and source.is_seekable and source.duration_ms:
                return source.duration_ms
        return None
