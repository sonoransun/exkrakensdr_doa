from __future__ import annotations

import argparse
import os
import sys

from PyQt6.QtWidgets import QApplication

from ._data.csv_file_source import CsvFileSource
from ._data.iq_file_source import IqFileSource
from ._data.live_ws_source import LiveWebSocketSource
from ._data.source_manager import SourceManager
from ._data.synthetic_source import SyntheticSignalConfig, SyntheticSource
from ._data.wav_file_source import WavFileSource
from ._dialogs.connect_dialog import ConnectDialog
from ._dialogs.open_file_dialog import detect_file_type, open_recording_file
from .main_window import MainWindow
from .settings_reader import SettingsReader


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="KrakenSDR Native Visualizer")
    parser.add_argument("--settings", type=str, default=None, help="Path to settings.json")
    parser.add_argument("--ws", type=str, default=None, help="WebSocket URL (e.g. ws://localhost:8021)")
    parser.add_argument("--file", type=str, default=None, help="Open a recording file (CSV, IQ, or WAV)")
    parser.add_argument("--synthetic", action="store_true", help="Start with synthetic data source")
    return parser.parse_args(argv)


def run_app(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    app = QApplication(sys.argv)
    app.setApplicationName("KrakenSDR Visualizer")

    # Determine root path of the project
    root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    # Settings reader
    settings_reader = SettingsReader(settings_path=args.settings, root_path=root_path)

    # Source manager
    source_manager = SourceManager()

    # Main window
    window = MainWindow(settings_reader, source_manager)

    # Wire up source panel actions
    window.source_panel.start_synthetic_requested.connect(lambda: _add_synthetic(source_manager))
    window.source_panel.open_file_requested.connect(lambda: _open_file(source_manager, window))
    window.source_panel.connect_live_requested.connect(lambda: _connect_live(source_manager, window))

    # Auto-start sources based on CLI args
    if args.synthetic:
        _add_synthetic(source_manager)
    if args.file:
        _add_file_source(source_manager, args.file)
    if args.ws:
        _add_ws_source(source_manager, args.ws)

    window.show()

    result = app.exec()

    # Cleanup
    source_manager.stop_all()
    return result


def _add_synthetic(source_manager: SourceManager):
    """Create and start a synthetic data source with demo signals."""
    if source_manager.get_source("synth:0"):
        return

    signals = [
        SyntheticSignalConfig(
            bearing_deg=45.0, power_dbm=-30.0, frequency_hz=394.3e6, drift_amplitude_deg=15.0, drift_period_sec=8.0
        ),
        SyntheticSignalConfig(bearing_deg=200.0, power_dbm=-40.0, frequency_hz=395.0e6, drift_rate_deg_per_sec=2.0),
        SyntheticSignalConfig(bearing_deg=310.0, power_dbm=-35.0, frequency_hz=396.5e6),
    ]
    source = SyntheticSource(source_id="synth:0", signals=signals, frame_rate_hz=10.0)
    source_manager.add_source("synth:0", source)
    source_manager.start_source("synth:0")


def _open_file(source_manager: SourceManager, parent_window):
    """Show a file dialog and add the selected file as a source."""
    path = open_recording_file(parent_window)
    if path:
        _add_file_source(source_manager, path)


def _add_file_source(source_manager: SourceManager, path: str):
    """Add a file source based on the file extension."""
    file_type = detect_file_type(path)
    source_id = f"file:{os.path.basename(path)}"

    # Remove existing source with same ID
    if source_manager.get_source(source_id):
        source_manager.remove_source(source_id)

    if file_type == "csv":
        source = CsvFileSource(path, source_id=source_id)
    elif file_type == "iq":
        source = IqFileSource(path, source_id=source_id)
    elif file_type == "wav":
        source = WavFileSource(path, source_id=source_id)
    else:
        return

    source_manager.add_source(source_id, source)
    source_manager.start_source(source_id)


def _connect_live(source_manager: SourceManager, parent_window):
    """Show a dialog and connect to a live WebSocket source."""
    dialog = ConnectDialog(parent_window)
    if dialog.exec():
        _add_ws_source(source_manager, f"ws://{dialog.host}:{dialog.port}")


def _add_ws_source(source_manager: SourceManager, ws_url: str):
    """Add a live WebSocket source from a URL like ws://host:port."""
    source_id = f"live:{ws_url}"
    if source_manager.get_source(source_id):
        return

    # Parse host and port from URL
    url = ws_url.replace("ws://", "").replace("wss://", "")
    parts = url.split(":")
    host = parts[0] if parts else "127.0.0.1"
    port = int(parts[1]) if len(parts) > 1 else 8021

    source = LiveWebSocketSource(source_id=source_id, host=host, port=port)
    source_manager.add_source(source_id, source)
    source_manager.start_source(source_id)
