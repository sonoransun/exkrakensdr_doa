from __future__ import annotations

from abc import abstractmethod

from PyQt6.QtCore import QMutex, QThread, pyqtSignal

from ..constants import SourceState


class BaseSource(QThread):
    """Abstract base for all data sources.

    Subclasses implement _run_loop() which is called from QThread.run().
    The base class manages state transitions and the frame signal.

    Signals cross threads via Qt's automatic queued connection, so
    frames emitted from the worker thread are safely delivered to
    GUI-thread widget slots without manual locking.
    """

    frame_ready = pyqtSignal(object)  # DoAFrame
    state_changed = pyqtSignal(object)  # SourceState
    error_occurred = pyqtSignal(str)
    progress_changed = pyqtSignal(float)  # 0.0-1.0 for file sources

    def __init__(self, source_id: str, parent=None):
        super().__init__(parent)
        self._source_id = source_id
        self._state = SourceState.STOPPED
        self._stop_requested = False
        self._pause_requested = False
        self._mutex = QMutex()

    @property
    def source_id(self) -> str:
        return self._source_id

    @property
    def source_state(self) -> SourceState:
        return self._state

    # --- Public API (called from main thread) ---

    def start_source(self):
        """Start or resume the source."""
        self._stop_requested = False
        self._pause_requested = False
        if self._state == SourceState.PAUSED:
            self._set_state(SourceState.RUNNING)
            return
        self.start()

    def pause_source(self):
        """Pause playback (file sources only; live sources ignore)."""
        self._pause_requested = True
        self._set_state(SourceState.PAUSED)

    def stop_source(self):
        """Request stop and wait up to 2s for thread to finish."""
        self._stop_requested = True
        self._pause_requested = False
        self.wait(2000)
        self._set_state(SourceState.STOPPED)

    # --- Seekable interface (file sources override) ---

    @property
    def is_seekable(self) -> bool:
        return False

    @property
    def duration_ms(self) -> int | None:
        return None

    def seek(self, position: float):
        """Seek to position 0.0-1.0. Only meaningful for file sources."""
        pass

    def set_playback_speed(self, speed: float):
        """Set playback speed multiplier. 1.0 = realtime."""
        pass

    # --- QThread entry point ---

    def run(self):
        self._set_state(SourceState.RUNNING)
        try:
            self._run_loop()
        except Exception as exc:
            self._set_state(SourceState.ERROR)
            self.error_occurred.emit(str(exc))
        else:
            if self._state != SourceState.ERROR:
                self._set_state(SourceState.FINISHED if not self._stop_requested else SourceState.STOPPED)

    @abstractmethod
    def _run_loop(self):
        """Produce frames in a loop.

        Must check self._stop_requested periodically and call
        self._emit_frame(frame) for each produced frame.
        Must respect self._pause_requested by sleeping.
        """
        ...

    def _emit_frame(self, frame):
        self.frame_ready.emit(frame)

    def _set_state(self, new_state: SourceState):
        self._state = new_state
        self.state_changed.emit(new_state)
