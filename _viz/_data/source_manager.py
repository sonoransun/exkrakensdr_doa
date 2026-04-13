from __future__ import annotations

from PyQt6.QtCore import QObject, pyqtSignal

from .data_frame import DoAFrame

# Sources can be BaseSource (QThread) or LiveWebSocketSource (QObject).
# Both provide: frame_ready, state_changed, start_source(), stop_source(),
# is_seekable, duration_ms, seek(), set_playback_speed(), deleteLater().
# We type as QObject to accept both.


class SourceManager(QObject):
    """Manages multiple concurrent data sources and aggregates their frames.

    Visualization widgets connect to the single frame_received signal
    rather than to individual sources.
    """

    frame_received = pyqtSignal(object)  # DoAFrame
    source_added = pyqtSignal(str)  # source_id
    source_removed = pyqtSignal(str)  # source_id
    source_state_changed = pyqtSignal(str, object)  # (source_id, SourceState)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._sources: dict[str, QObject] = {}
        self._latest_frames: dict[str, DoAFrame] = {}
        self._visibility: dict[str, bool] = {}

    def add_source(self, source_id: str, source):
        if source_id in self._sources:
            self.remove_source(source_id)
        self._sources[source_id] = source
        self._visibility[source_id] = True
        source.frame_ready.connect(lambda frame, sid=source_id: self._on_frame(sid, frame))
        source.state_changed.connect(lambda state, sid=source_id: self.source_state_changed.emit(sid, state))
        self.source_added.emit(source_id)

    def remove_source(self, source_id: str):
        if source_id in self._sources:
            source = self._sources.pop(source_id)
            source.stop_source()
            source.deleteLater()
            self._latest_frames.pop(source_id, None)
            self._visibility.pop(source_id, None)
            self.source_removed.emit(source_id)

    def start_source(self, source_id: str):
        source = self._sources.get(source_id)
        if source:
            source.start_source()

    def stop_source(self, source_id: str):
        source = self._sources.get(source_id)
        if source:
            source.stop_source()

    def start_all(self):
        for source in self._sources.values():
            source.start_source()

    def stop_all(self):
        for source in self._sources.values():
            source.stop_source()

    def get_source(self, source_id: str):
        return self._sources.get(source_id)

    def set_visible(self, source_id: str, visible: bool):
        self._visibility[source_id] = visible

    def is_visible(self, source_id: str) -> bool:
        return self._visibility.get(source_id, True)

    @property
    def source_ids(self) -> list[str]:
        return list(self._sources.keys())

    @property
    def latest_frames(self) -> dict[str, DoAFrame]:
        return dict(self._latest_frames)

    def _on_frame(self, source_id: str, frame: DoAFrame):
        self._latest_frames[source_id] = frame
        if self._visibility.get(source_id, True):
            self.frame_received.emit(frame)
