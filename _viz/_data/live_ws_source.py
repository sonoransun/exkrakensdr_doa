from __future__ import annotations

import json
import time

import numpy as np
from PyQt6.QtCore import QObject, QTimer, QUrl, pyqtSignal
from PyQt6.QtWebSockets import QWebSocket

from ..constants import DOA_ARRAY_SIZE, SourceKind, SourceState
from .data_frame import DoAFrame


class LiveWebSocketSource(QObject):
    """WebSocket client that connects to the Node.js middleware (port 8021).

    Runs on the main thread using Qt's event-driven QWebSocket.
    Parses incoming JSON frames into DoAFrame objects.
    Auto-reconnects on disconnect with a 2-second timer.

    Unlike file/synthetic sources (QThread-based), this is a QObject
    since QWebSocket requires a Qt event loop. It provides the same
    signals as BaseSource for compatibility with SourceManager.
    """

    frame_ready = pyqtSignal(object)  # DoAFrame
    state_changed = pyqtSignal(object)  # SourceState
    error_occurred = pyqtSignal(str)
    progress_changed = pyqtSignal(float)  # always 0.0 for live

    def __init__(self, source_id: str = "live:ws", host: str = "127.0.0.1", port: int = 8021, parent=None):
        super().__init__(parent)
        self._source_id = source_id
        self._host = host
        self._port = port
        self._state = SourceState.STOPPED
        self._stop_requested = False

        self._ws = QWebSocket()
        self._ws.textMessageReceived.connect(self._on_message)
        self._ws.connected.connect(self._on_connected)
        self._ws.disconnected.connect(self._on_disconnected)
        self._ws.errorOccurred.connect(self._on_error)

        self._reconnect_timer = QTimer(self)
        self._reconnect_timer.setInterval(2000)
        self._reconnect_timer.setSingleShot(True)
        self._reconnect_timer.timeout.connect(self._connect)

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def source_state(self) -> SourceState:
        return self._state

    @property
    def is_seekable(self) -> bool:
        return False

    @property
    def duration_ms(self) -> int | None:
        return None

    def seek(self, position: float):
        pass

    def set_playback_speed(self, speed: float):
        pass

    def start_source(self):
        self._stop_requested = False
        self._connect()

    def pause_source(self):
        pass  # Live sources cannot be paused

    def stop_source(self):
        self._stop_requested = True
        self._reconnect_timer.stop()
        self._ws.close()
        self._set_state(SourceState.STOPPED)

    def wait(self, msecs: int = 2000):
        pass  # No thread to wait on

    def deleteLater(self):
        self.stop_source()
        super().deleteLater()

    def _connect(self):
        url = QUrl(f"ws://{self._host}:{self._port}")
        self._ws.open(url)

    def _on_connected(self):
        self._set_state(SourceState.RUNNING)

    def _on_message(self, raw: str):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            return

        # Skip ping/settings messages (they have a "type" field)
        if "type" in data:
            return

        frame = self._parse_json(data)
        if frame:
            self.frame_ready.emit(frame)

    def _on_disconnected(self):
        if not self._stop_requested:
            self._set_state(SourceState.ERROR)
            self._reconnect_timer.start()

    def _on_error(self, error):
        if not self._stop_requested:
            self.error_occurred.emit(f"WebSocket error: {error}")
            self._reconnect_timer.start()

    def _set_state(self, new_state: SourceState):
        self._state = new_state
        self.state_changed.emit(new_state)

    def _parse_json(self, data: dict) -> DoAFrame | None:
        """Parse a middleware JSON frame into a DoAFrame."""
        try:
            # Parse DoA array from comma-separated string
            doa_array_raw = data.get("doaArray", "")
            if isinstance(doa_array_raw, str):
                parts = [p.strip() for p in doa_array_raw.split(",") if p.strip()]
                doa_array = np.array([float(x) for x in parts], dtype=np.float32)
            else:
                doa_array = np.array(doa_array_raw, dtype=np.float32)

            # Pad or truncate to 360
            if doa_array.size < DOA_ARRAY_SIZE:
                doa_array = np.pad(doa_array, (0, DOA_ARRAY_SIZE - doa_array.size))
            elif doa_array.size > DOA_ARRAY_SIZE:
                doa_array = doa_array[:DOA_ARRAY_SIZE]

            return DoAFrame(
                source_id=self._source_id,
                source_kind=SourceKind.LIVE_WS,
                timestamp_ms=int(data.get("tStamp", time.time() * 1000)),
                frequency_hz=float(data.get("freq", 0)),
                bearing_deg=float(data.get("radioBearing", 0)),
                doa_array=doa_array,
                confidence=float(data.get("conf", 0)),
                power_dbm=float(data.get("power", -120)),
                snr_db=float(data.get("snr_db", 0)),
                station_id=str(data.get("station_id", "")),
                latitude=float(data.get("latitude", 0)),
                longitude=float(data.get("longitude", 0)),
                antenna_type=str(data.get("antType", "UCA")),
            )
        except (ValueError, TypeError):
            return None
