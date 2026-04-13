from __future__ import annotations

import json
import logging
import os

from PyQt6.QtCore import QFileSystemWatcher, QObject, QTimer, pyqtSignal

from .constants import DEFAULT_SETTINGS_PATH

logger = logging.getLogger(__name__)


class SettingsReader(QObject):
    """Watches _share/settings.json and emits parsed settings on change.

    Uses QFileSystemWatcher for OS-level file notifications. Falls back to
    a 1-second QTimer poll if the watcher fails to detect changes.
    """

    settings_changed = pyqtSignal(dict)

    def __init__(self, settings_path: str | None = None, root_path: str | None = None, parent=None):
        super().__init__(parent)
        if root_path is None:
            root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if settings_path is None:
            settings_path = os.path.join(root_path, DEFAULT_SETTINGS_PATH)

        self._settings_path = settings_path
        self._settings: dict = {}
        self._last_mtime: float = 0.0

        # Try OS-level watcher
        self._watcher = QFileSystemWatcher()
        if os.path.exists(self._settings_path):
            self._watcher.addPath(self._settings_path)
        self._watcher.fileChanged.connect(self._on_file_changed)

        # Fallback poll timer (handles cases where watcher misses events)
        self._poll_timer = QTimer(self)
        self._poll_timer.setInterval(1000)
        self._poll_timer.timeout.connect(self._poll_check)
        self._poll_timer.start()

        # Initial load
        self._reload()

    @property
    def settings(self) -> dict:
        return self._settings

    def get(self, key: str, default=None):
        return self._settings.get(key, default)

    def _on_file_changed(self, path: str):
        self._reload()
        # QFileSystemWatcher may remove the path after a change; re-add it
        if path not in self._watcher.files():
            if os.path.exists(path):
                self._watcher.addPath(path)

    def _poll_check(self):
        if not os.path.exists(self._settings_path):
            return
        try:
            mtime = os.stat(self._settings_path).st_mtime
        except OSError:
            return
        if mtime != self._last_mtime:
            self._reload()

    def _reload(self):
        if not os.path.exists(self._settings_path):
            logger.debug("Settings file not found: %s", self._settings_path)
            return
        try:
            mtime = os.stat(self._settings_path).st_mtime
            with open(self._settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Failed to read settings: %s", exc)
            return

        self._last_mtime = mtime
        self._settings = data
        self.settings_changed.emit(data)

    # --- Convenience accessors for common settings ---

    @property
    def center_freq(self) -> float:
        return float(self._settings.get("center_freq", 0))

    @property
    def compass_offset(self) -> float:
        return float(self._settings.get("compass_offset", 0))

    @property
    def antenna_arrangement(self) -> str:
        return str(self._settings.get("ant_arrangement", "UCA"))

    @property
    def antenna_spacing(self) -> float:
        return float(self._settings.get("ant_spacing_meters", 0.0))

    @property
    def active_vfos(self) -> int:
        return int(self._settings.get("active_vfos", 1))

    @property
    def station_id(self) -> str:
        return str(self._settings.get("station_id", ""))

    @property
    def latitude(self) -> float:
        return float(self._settings.get("latitude", 0.0))

    @property
    def longitude(self) -> float:
        return float(self._settings.get("longitude", 0.0))
