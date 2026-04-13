import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _viz._data.data_frame import DoAFrame
from _viz._data.source_manager import SourceManager
from _viz._data.synthetic_source import SyntheticSignalConfig, SyntheticSource
from _viz.constants import SourceKind, SourceState


class TestSourceManager:
    def test_add_and_remove_source(self, qtbot):
        mgr = SourceManager()
        src = SyntheticSource(source_id="synth:0", frame_rate_hz=100.0)

        added = []
        mgr.source_added.connect(lambda sid: added.append(sid))

        mgr.add_source("synth:0", src)
        assert "synth:0" in mgr.source_ids
        assert len(added) == 1

        removed = []
        mgr.source_removed.connect(lambda sid: removed.append(sid))
        mgr.remove_source("synth:0")
        assert "synth:0" not in mgr.source_ids
        assert len(removed) == 1

    def test_frame_routing(self, qtbot):
        mgr = SourceManager()
        received = []
        mgr.frame_received.connect(lambda f: received.append(f))

        src = SyntheticSource(source_id="synth:0", frame_rate_hz=100.0)
        mgr.add_source("synth:0", src)

        # Manually emit a frame
        frame = DoAFrame(source_id="synth:0", source_kind=SourceKind.SYNTHETIC, timestamp_ms=1000, bearing_deg=45.0)
        src.frame_ready.emit(frame)

        assert len(received) == 1
        assert received[0].bearing_deg == 45.0

    def test_visibility_toggle(self, qtbot):
        mgr = SourceManager()
        received = []
        mgr.frame_received.connect(lambda f: received.append(f))

        src = SyntheticSource(source_id="synth:0", frame_rate_hz=100.0)
        mgr.add_source("synth:0", src)

        # Visible by default
        frame = DoAFrame(source_id="synth:0", source_kind=SourceKind.SYNTHETIC, timestamp_ms=1000)
        src.frame_ready.emit(frame)
        assert len(received) == 1

        # Hide source
        mgr.set_visible("synth:0", False)
        src.frame_ready.emit(frame)
        assert len(received) == 1  # no new frame received

        # Show again
        mgr.set_visible("synth:0", True)
        src.frame_ready.emit(frame)
        assert len(received) == 2

    def test_latest_frames(self, qtbot):
        mgr = SourceManager()
        src = SyntheticSource(source_id="synth:0", frame_rate_hz=100.0)
        mgr.add_source("synth:0", src)

        frame1 = DoAFrame(source_id="synth:0", source_kind=SourceKind.SYNTHETIC, timestamp_ms=1000, bearing_deg=10.0)
        src.frame_ready.emit(frame1)
        assert mgr.latest_frames["synth:0"].bearing_deg == 10.0

        frame2 = DoAFrame(source_id="synth:0", source_kind=SourceKind.SYNTHETIC, timestamp_ms=2000, bearing_deg=20.0)
        src.frame_ready.emit(frame2)
        assert mgr.latest_frames["synth:0"].bearing_deg == 20.0

    def test_state_change_signal(self, qtbot):
        mgr = SourceManager()
        states = []
        mgr.source_state_changed.connect(lambda sid, st: states.append((sid, st)))

        src = SyntheticSource(source_id="synth:0", frame_rate_hz=100.0)
        mgr.add_source("synth:0", src)

        src.state_changed.emit(SourceState.RUNNING)
        assert len(states) == 1
        assert states[0] == ("synth:0", SourceState.RUNNING)

    def test_replace_source(self, qtbot):
        mgr = SourceManager()
        src1 = SyntheticSource(source_id="synth:0", frame_rate_hz=100.0)
        src2 = SyntheticSource(source_id="synth:0", frame_rate_hz=50.0)

        mgr.add_source("synth:0", src1)
        mgr.add_source("synth:0", src2)

        assert mgr.get_source("synth:0") is src2
        assert len(mgr.source_ids) == 1
