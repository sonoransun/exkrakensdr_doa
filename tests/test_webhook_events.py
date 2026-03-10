import time

import pytest

from webhook_events import (
    EventType,
    FrequencyHistory,
    VFOSignalState,
    WebhookEvent,
    WebhookEventDetector,
)


class TestWebhookEvent:
    def test_to_dict_omits_none_fields(self):
        event = WebhookEvent(
            event_type="signal_appear",
            timestamp=1000,
            vfo_index=0,
            frequency_hz=100e6,
            station_id="TEST",
            latitude=0.0,
            longitude=0.0,
        )
        d = event.to_dict()
        assert "bearing_deg" not in d
        assert "confidence" not in d
        assert "power_dbm" not in d
        assert d["event_type"] == "signal_appear"
        assert d["vfo_index"] == 0

    def test_to_dict_includes_set_fields(self):
        event = WebhookEvent(
            event_type="doa_change",
            timestamp=2000,
            vfo_index=1,
            frequency_hz=200e6,
            station_id="TEST",
            latitude=1.0,
            longitude=2.0,
            bearing_deg=45.0,
            confidence=0.9,
        )
        d = event.to_dict()
        assert d["bearing_deg"] == 45.0
        assert d["confidence"] == 0.9


class TestFrequencyHistory:
    def test_novel_detection(self):
        fh = FrequencyHistory(window_sec=3600, tolerance_hz=5000)
        assert fh.is_novel(100e6) is True
        fh.record(100e6)
        assert fh.is_novel(100e6) is False

    def test_known_not_novel(self):
        fh = FrequencyHistory(window_sec=3600, tolerance_hz=5000)
        fh.record(100e6)
        assert fh.is_novel(100e6) is False

    def test_pruning_after_window(self):
        fh = FrequencyHistory(window_sec=1.0, tolerance_hz=5000)
        fh.record(100e6)
        # Manually backdate the entry
        canonical = fh._canonicalize(100e6)
        fh._seen[canonical] = time.time() - 2.0
        assert fh.is_novel(100e6) is True

    def test_canonicalization(self):
        fh = FrequencyHistory(window_sec=3600, tolerance_hz=5000)
        fh.record(100_001_000)
        # 100_002_000 should canonicalize to same bucket (100_000_000) as 100_001_000
        assert fh.is_novel(100_002_000) is False
        # 100_004_000 canonicalizes to 100_005_000, different bucket
        assert fh.is_novel(100_004_000) is True

    def test_zero_tolerance_edge(self):
        fh = FrequencyHistory(window_sec=3600, tolerance_hz=0)
        fh.record(100e6)
        assert fh.is_novel(100e6) is False
        # Even 1 Hz different should be novel with zero tolerance
        assert fh.is_novel(100e6 + 1) is True


class TestWebhookEventDetector:
    def _make_detector(self, max_vfos=4):
        d = WebhookEventDetector(max_vfos=max_vfos)
        d.enabled = True
        d.evt_signal_appear = True
        d.evt_signal_disappear = True
        d.evt_novel_freq = True
        d.evt_doa_change = True
        d.evt_power_alert = True
        return d

    def test_disabled_emits_nothing(self):
        d = WebhookEventDetector(max_vfos=4)
        d.enabled = False
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        assert len(d.drain_events()) == 0

    def test_signal_appear(self):
        d = self._make_detector()
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        events = d.drain_events()
        appear_events = [e for e in events if e.event_type == EventType.SIGNAL_APPEAR.value]
        assert len(appear_events) == 1
        assert appear_events[0].frequency_hz == 100e6
        assert appear_events[0].bearing_deg == 90.0

    def test_signal_disappear(self):
        d = self._make_detector()
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        d.drain_events()
        d.on_signal_lost(0, 100e6, "TEST", 0, 0, 2000)
        events = d.drain_events()
        disappear_events = [e for e in events if e.event_type == EventType.SIGNAL_DISAPPEAR.value]
        assert len(disappear_events) == 1

    def test_novel_frequency_allowlist(self):
        d = self._make_detector()
        d.known_frequencies = [200e6]
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        events = d.drain_events()
        novel_events = [e for e in events if e.event_type == EventType.NOVEL_FREQUENCY.value]
        assert len(novel_events) == 1
        assert novel_events[0].novelty_method == "allowlist"

    def test_novel_frequency_autolearn(self):
        d = self._make_detector()
        d.autolearn_enabled = True
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        events = d.drain_events()
        novel_events = [e for e in events if e.event_type == EventType.NOVEL_FREQUENCY.value]
        assert len(novel_events) == 1
        assert novel_events[0].novelty_method == "autolearn"

    def test_doa_change_above_threshold(self):
        d = self._make_detector()
        d.doa_change_threshold_deg = 10.0
        # First detection establishes bearing
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        d.drain_events()
        # Second detection with big bearing change
        d.on_signal_detected(0, 100e6, 120.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 2000)
        events = d.drain_events()
        doa_events = [e for e in events if e.event_type == EventType.DOA_CHANGE.value]
        assert len(doa_events) == 1
        assert doa_events[0].bearing_change_deg == 30.0

    def test_doa_change_below_threshold(self):
        d = self._make_detector()
        d.doa_change_threshold_deg = 10.0
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        d.drain_events()
        d.on_signal_detected(0, 100e6, 95.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 2000)
        events = d.drain_events()
        doa_events = [e for e in events if e.event_type == EventType.DOA_CHANGE.value]
        assert len(doa_events) == 0

    def test_doa_change_wraparound(self):
        d = self._make_detector()
        d.doa_change_threshold_deg = 5.0
        d.on_signal_detected(0, 100e6, 355.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        d.drain_events()
        d.on_signal_detected(0, 100e6, 5.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 2000)
        events = d.drain_events()
        doa_events = [e for e in events if e.event_type == EventType.DOA_CHANGE.value]
        assert len(doa_events) == 1
        assert doa_events[0].bearing_change_deg == 10.0

    def test_power_alert_high(self):
        d = self._make_detector()
        d.power_high_threshold_dbm = -30.0
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -20.0, 10.0, "TEST", 0, 0, 1000)
        events = d.drain_events()
        power_events = [e for e in events if e.event_type == EventType.POWER_ALERT.value]
        assert len(power_events) == 1
        assert power_events[0].power_threshold_crossed == "high"

    def test_power_alert_hysteresis(self):
        d = self._make_detector()
        d.power_high_threshold_dbm = -30.0
        # Trigger high alert
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -20.0, 10.0, "TEST", 0, 0, 1000)
        d.drain_events()
        # Same high power - should NOT retrigger
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -20.0, 10.0, "TEST", 0, 0, 2000)
        events = d.drain_events()
        power_events = [e for e in events if e.event_type == EventType.POWER_ALERT.value]
        assert len(power_events) == 0

    def test_drain_events_clears_queue(self):
        d = self._make_detector()
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        events = d.drain_events()
        assert len(events) > 0
        # Second drain should be empty
        events2 = d.drain_events()
        assert len(events2) == 0

    def test_vfo_index_out_of_bounds(self):
        d = self._make_detector(max_vfos=4)
        # Should not raise
        d.on_signal_detected(99, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        d.on_signal_lost(99, 100e6, "TEST", 0, 0, 2000)
        assert len(d.drain_events()) == 0

    def test_event_toggle_respected(self):
        d = self._make_detector()
        d.evt_signal_appear = False
        d.on_signal_detected(0, 100e6, 90.0, 0.8, -50.0, 10.0, "TEST", 0, 0, 1000)
        events = d.drain_events()
        appear_events = [e for e in events if e.event_type == EventType.SIGNAL_APPEAR.value]
        assert len(appear_events) == 0
