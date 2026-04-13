from __future__ import annotations

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from .._data.source_manager import SourceManager
from ..constants import SourceState


class SourcePanel(QWidget):
    """Sidebar panel for managing data sources: add, remove, toggle visibility."""

    connect_live_requested = pyqtSignal()
    open_file_requested = pyqtSignal()
    start_synthetic_requested = pyqtSignal()

    def __init__(self, source_manager: SourceManager, parent=None):
        super().__init__(parent)
        self._source_manager = source_manager

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Title
        title = QLabel("Data Sources")
        title.setStyleSheet("font-weight: bold; font-size: 13px; color: #cccccc;")
        layout.addWidget(title)

        # Action buttons
        btn_layout = QVBoxLayout()

        self._btn_live = QPushButton("Connect Live")
        self._btn_live.clicked.connect(self.connect_live_requested.emit)
        btn_layout.addWidget(self._btn_live)

        self._btn_file = QPushButton("Open File")
        self._btn_file.clicked.connect(self.open_file_requested.emit)
        btn_layout.addWidget(self._btn_file)

        self._btn_synth = QPushButton("Start Synthetic")
        self._btn_synth.clicked.connect(self.start_synthetic_requested.emit)
        btn_layout.addWidget(self._btn_synth)

        layout.addLayout(btn_layout)

        # Source list area
        self._sources_group = QGroupBox("Active Sources")
        self._sources_group.setStyleSheet("""
            QGroupBox {
                color: #cccccc;
                border: 1px solid #444444;
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 16px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 8px;
            }
            """)
        self._sources_layout = QVBoxLayout(self._sources_group)
        layout.addWidget(self._sources_group)

        # Source entries: {source_id: SourceEntry widget}
        self._entries: dict[str, SourceEntry] = {}

        layout.addStretch()

        # Connect manager signals
        source_manager.source_added.connect(self._on_source_added)
        source_manager.source_removed.connect(self._on_source_removed)
        source_manager.source_state_changed.connect(self._on_source_state_changed)

    def _on_source_added(self, source_id: str):
        entry = SourceEntry(source_id)
        entry.visibility_changed.connect(lambda v, sid=source_id: self._source_manager.set_visible(sid, v))
        entry.remove_requested.connect(lambda sid=source_id: self._source_manager.remove_source(sid))
        self._entries[source_id] = entry
        self._sources_layout.addWidget(entry)

    def _on_source_removed(self, source_id: str):
        entry = self._entries.pop(source_id, None)
        if entry:
            self._sources_layout.removeWidget(entry)
            entry.deleteLater()

    def _on_source_state_changed(self, source_id: str, state: SourceState):
        entry = self._entries.get(source_id)
        if entry:
            entry.set_state(state)


class SourceEntry(QWidget):
    """Single source entry with visibility toggle, label, state indicator, and remove button."""

    visibility_changed = pyqtSignal(bool)
    remove_requested = pyqtSignal()

    def __init__(self, source_id: str, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)

        self._checkbox = QCheckBox()
        self._checkbox.setChecked(True)
        self._checkbox.toggled.connect(self.visibility_changed.emit)
        layout.addWidget(self._checkbox)

        self._label = QLabel(source_id)
        self._label.setStyleSheet("color: #cccccc;")
        layout.addWidget(self._label, stretch=1)

        self._state_label = QLabel("\u25cf")  # circle indicator
        self._state_label.setStyleSheet("color: #888888;")
        layout.addWidget(self._state_label)

        self._remove_btn = QPushButton("\u2715")
        self._remove_btn.setFixedSize(20, 20)
        self._remove_btn.setStyleSheet("color: #ff6666; border: none;")
        self._remove_btn.clicked.connect(self.remove_requested.emit)
        layout.addWidget(self._remove_btn)

    def set_state(self, state: SourceState):
        colors = {
            SourceState.STOPPED: "#888888",
            SourceState.RUNNING: "#00cc66",
            SourceState.PAUSED: "#ffaa00",
            SourceState.ERROR: "#ff3333",
            SourceState.FINISHED: "#6666ff",
        }
        self._state_label.setStyleSheet(f"color: {colors.get(state, '#888888')};")
