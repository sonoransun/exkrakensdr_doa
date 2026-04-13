from __future__ import annotations

from PyQt6.QtWidgets import QFileDialog, QWidget

FILE_FILTERS = "All Supported (*.csv *.iq *.wav);;CSV Logs (*.csv);;IQ Files (*.iq);;WAV Files (*.wav)"


def open_recording_file(parent: QWidget | None = None) -> str | None:
    """Show a file dialog to select a recording file. Returns the path or None."""
    path, _ = QFileDialog.getOpenFileName(parent, "Open Recording", "", FILE_FILTERS)
    return path if path else None


def detect_file_type(path: str) -> str | None:
    """Detect the recording file type from its extension."""
    lower = path.lower()
    if lower.endswith(".csv"):
        return "csv"
    elif lower.endswith(".iq"):
        return "iq"
    elif lower.endswith(".wav"):
        return "wav"
    return None
