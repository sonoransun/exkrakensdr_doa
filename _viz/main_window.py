from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ._data.data_frame import DoAFrame
from ._data.source_manager import SourceManager
from ._widgets.bearing_history_widget import BearingHistoryWidget
from ._widgets.doa_compass_widget import DoACompassWidget
from ._widgets.overlay_legend import OverlayLegend
from ._widgets.source_panel import SourcePanel
from ._widgets.spatial_3d_widget import Spatial3DWidget
from ._widgets.spectrum_widget import SpectrumWidget
from ._widgets.timeline_widget import TimelineWidget
from ._widgets.vfo_table_widget import VfoTableWidget
from .settings_reader import SettingsReader


class MainWindow(QMainWindow):
    """Main application window with tabbed visualization panels and status bar."""

    def __init__(self, settings_reader: SettingsReader, source_manager: SourceManager, parent=None):
        super().__init__(parent)
        self._settings = settings_reader
        self._source_manager = source_manager

        self.setWindowTitle("KrakenSDR Visualizer")
        self.setMinimumSize(1024, 700)

        # Dark theme
        self.setStyleSheet(DARK_STYLESHEET)

        # --- Central area with splitter ---
        central = QWidget()
        central_layout = QHBoxLayout(central)
        central_layout.setContentsMargins(4, 4, 4, 4)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: source panel
        self._source_panel = SourcePanel(source_manager)
        self._source_panel.setFixedWidth(200)
        splitter.addWidget(self._source_panel)

        # Right: tabs + timeline in a vertical layout
        self._tabs = QTabWidget()
        self._timeline = TimelineWidget(source_manager)

        self._overlay_legend = OverlayLegend()

        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(self._tabs, stretch=1)
        right_layout.addWidget(self._overlay_legend)
        right_layout.addWidget(self._timeline)

        splitter.addWidget(right_widget)
        splitter.setStretchFactor(1, 1)

        central_layout.addWidget(splitter)
        self.setCentralWidget(central)

        # --- DoA tab ---
        doa_tab = QWidget()
        doa_layout = QVBoxLayout(doa_tab)

        # Compass + table side by side
        doa_splitter = QSplitter(Qt.Orientation.Horizontal)
        self._compass = DoACompassWidget(compass_offset=settings_reader.compass_offset)
        doa_splitter.addWidget(self._compass)

        self._vfo_table = VfoTableWidget()
        doa_splitter.addWidget(self._vfo_table)
        doa_splitter.setStretchFactor(0, 2)
        doa_splitter.setStretchFactor(1, 1)

        # Bearing history below compass/table
        self._bearing_history = BearingHistoryWidget()
        doa_splitter_v = QSplitter(Qt.Orientation.Vertical)
        doa_splitter_v.addWidget(doa_splitter)
        doa_splitter_v.addWidget(self._bearing_history)
        doa_splitter_v.setStretchFactor(0, 2)
        doa_splitter_v.setStretchFactor(1, 1)

        doa_layout.addWidget(doa_splitter_v)
        self._tabs.addTab(doa_tab, "DoA Compass")

        # --- Spectrum tab ---
        self._spectrum = SpectrumWidget()
        self._tabs.addTab(self._spectrum, "Spectrum")

        # --- 3D spatial view tab ---
        self._spatial_3d = Spatial3DWidget()
        self._tabs.addTab(self._spatial_3d, "3D View")

        # --- Status bar ---
        self._status_bar = QStatusBar()
        self.setStatusBar(self._status_bar)

        self._freq_label = QLabel()
        self._antenna_label = QLabel()
        self._station_label = QLabel()
        self._settings_label = QLabel()
        self._frame_rate_label = QLabel()

        self._status_bar.addPermanentWidget(self._freq_label)
        self._status_bar.addPermanentWidget(self._antenna_label)
        self._status_bar.addPermanentWidget(self._station_label)
        self._status_bar.addPermanentWidget(self._settings_label)
        self._status_bar.addPermanentWidget(self._frame_rate_label)

        # Menu bar (must be after source panel is created)
        self._build_menu_bar()

        # --- Connect signals ---
        self._settings.settings_changed.connect(self._on_settings_changed)
        self._source_manager.frame_received.connect(self._on_frame)
        self._source_manager.source_removed.connect(self._on_source_removed)
        self._update_status_bar()

        # Frame counter for rate display
        self._frame_count = 0

    def _on_frame(self, frame: DoAFrame):
        """Route incoming frames to all visualization widgets."""
        self._compass.on_frame(frame)
        self._vfo_table.on_frame(frame)
        self._bearing_history.on_frame(frame)
        self._spectrum.on_frame(frame)
        self._spatial_3d.on_frame(frame)
        if frame.file_position > 0:
            self._timeline.on_progress(frame.file_position)
        self._frame_count += 1
        if self._frame_count % 10 == 0:
            self._frame_rate_label.setText(f"  Frames: {self._frame_count}  ")

    def _on_source_removed(self, source_id: str):
        self._compass.remove_source(source_id)
        self._vfo_table.remove_source(source_id)
        self._bearing_history.remove_source(source_id)
        self._spectrum.remove_source(source_id)
        self._spatial_3d.remove_source(source_id)

    def _on_settings_changed(self, settings: dict):
        self._update_status_bar()
        self._compass.set_compass_offset(self._settings.compass_offset)
        self._spatial_3d.update_settings(settings)

    def _update_status_bar(self):
        freq_mhz = self._settings.center_freq / 1e6 if self._settings.center_freq else 0
        self._freq_label.setText(f"  Freq: {freq_mhz:.3f} MHz  ")
        self._antenna_label.setText(f"  Ant: {self._settings.antenna_arrangement}  ")
        self._station_label.setText(f"  Station: {self._settings.station_id or '(none)'}  ")

        if self._settings.settings:
            self._settings_label.setText("  Settings: loaded  ")
        else:
            self._settings_label.setText("  Settings: not found  ")

    @property
    def tabs(self) -> QTabWidget:
        return self._tabs

    @property
    def source_panel(self) -> SourcePanel:
        return self._source_panel

    @property
    def compass(self) -> DoACompassWidget:
        return self._compass

    @property
    def vfo_table(self) -> VfoTableWidget:
        return self._vfo_table

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        open_action = QAction("&Open Recording...", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._source_panel.open_file_requested.emit)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        quit_action = QAction("&Quit", self)
        quit_action.setShortcut(QKeySequence("Ctrl+Q"))
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)

        # Connect menu
        connect_menu = menu_bar.addMenu("&Connect")

        live_action = QAction("&Live Source...", self)
        live_action.setShortcut(QKeySequence("Ctrl+L"))
        live_action.triggered.connect(self._source_panel.connect_live_requested.emit)
        connect_menu.addAction(live_action)

        synth_action = QAction("&Synthetic Data", self)
        synth_action.setShortcut(QKeySequence("Ctrl+G"))
        synth_action.triggered.connect(self._source_panel.start_synthetic_requested.emit)
        connect_menu.addAction(synth_action)

        # View menu
        view_menu = menu_bar.addMenu("&View")

        for i, name in enumerate(["DoA Compass", "Spectrum", "3D View"]):
            action = QAction(f"&{name}", self)
            action.setShortcut(QKeySequence(f"Ctrl+{i + 1}"))
            tab_idx = i
            action.triggered.connect(lambda checked, idx=tab_idx: self._tabs.setCurrentIndex(idx))
            view_menu.addAction(action)

    def keyPressEvent(self, event):
        """Handle keyboard shortcuts for playback control."""
        key = event.key()
        if key == Qt.Key.Key_Space:
            self._timeline._toggle_play_pause()
        elif key == Qt.Key.Key_Left:
            # Seek back ~5%
            current = self._timeline._slider.value()
            self._timeline._slider.setValue(max(0, current - 50))
            self._timeline._on_seek(self._timeline._slider.value())
        elif key == Qt.Key.Key_Right:
            # Seek forward ~5%
            current = self._timeline._slider.value()
            self._timeline._slider.setValue(min(1000, current + 50))
            self._timeline._on_seek(self._timeline._slider.value())
        elif key == Qt.Key.Key_Plus or key == Qt.Key.Key_Equal:
            idx = self._timeline._speed_combo.currentIndex()
            if idx < self._timeline._speed_combo.count() - 1:
                self._timeline._speed_combo.setCurrentIndex(idx + 1)
        elif key == Qt.Key.Key_Minus:
            idx = self._timeline._speed_combo.currentIndex()
            if idx > 0:
                self._timeline._speed_combo.setCurrentIndex(idx - 1)
        else:
            super().keyPressEvent(event)


DARK_STYLESHEET = """
QMainWindow, QWidget {
    background-color: #1e1e1e;
    color: #cccccc;
}
QMenuBar {
    background-color: #2d2d2d;
    color: #cccccc;
    border-bottom: 1px solid #444;
}
QMenuBar::item:selected {
    background-color: #444;
}
QMenu {
    background-color: #2d2d2d;
    color: #cccccc;
    border: 1px solid #444;
}
QMenu::item:selected {
    background-color: #444;
}
QTabWidget::pane {
    border: 1px solid #444;
    background-color: #1e1e1e;
}
QTabBar::tab {
    background-color: #2d2d2d;
    color: #cccccc;
    padding: 6px 16px;
    border: 1px solid #444;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}
QTabBar::tab:selected {
    background-color: #1e1e1e;
    border-bottom: 1px solid #1e1e1e;
}
QTabBar::tab:hover {
    background-color: #383838;
}
QStatusBar {
    background-color: #2d2d2d;
    color: #999999;
    border-top: 1px solid #444;
}
QSplitter::handle {
    background-color: #444;
}
QSplitter::handle:horizontal {
    width: 3px;
}
QSplitter::handle:vertical {
    height: 3px;
}
QSlider::groove:horizontal {
    background-color: #444;
    height: 4px;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #888;
    width: 12px;
    margin: -4px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover {
    background-color: #aaa;
}
"""
