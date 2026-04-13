import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _viz._data.data_frame import DOA_ARRAY_SIZE
from _viz._data.synthetic_source import SyntheticSignalConfig, SyntheticSource
from _viz.constants import SourceKind


class TestSyntheticSignalConfig:
    def test_defaults(self):
        cfg = SyntheticSignalConfig()
        assert cfg.bearing_deg == 90.0
        assert cfg.power_dbm == -30.0
        assert cfg.drift_rate_deg_per_sec == 0.0

    def test_custom_values(self):
        cfg = SyntheticSignalConfig(bearing_deg=180.0, power_dbm=-50.0, drift_rate_deg_per_sec=5.0)
        assert cfg.bearing_deg == 180.0
        assert cfg.power_dbm == -50.0


class TestSyntheticSource:
    def _make_source(self, **kwargs):
        return SyntheticSource(source_id="test:synth", **kwargs)

    def test_generate_frame_shape(self):
        src = self._make_source()
        cfg = SyntheticSignalConfig(bearing_deg=45.0)
        frame = src._generate_frame(cfg, 0, 0.0)
        assert frame.doa_array.shape == (DOA_ARRAY_SIZE,)
        assert frame.doa_array.dtype == np.float32

    def test_peak_at_configured_bearing(self):
        src = self._make_source()
        for bearing in [0, 45, 90, 180, 270, 359]:
            cfg = SyntheticSignalConfig(bearing_deg=float(bearing))
            frame = src._generate_frame(cfg, 0, 0.0)
            peak_idx = int(np.argmax(frame.doa_array))
            # Peak should be within 2 degrees of configured bearing
            diff = min(abs(peak_idx - bearing), DOA_ARRAY_SIZE - abs(peak_idx - bearing))
            assert diff <= 2, f"Expected peak near {bearing}, got {peak_idx}"

    def test_frame_metadata(self):
        src = self._make_source()
        cfg = SyntheticSignalConfig(bearing_deg=90.0, frequency_hz=400e6)
        frame = src._generate_frame(cfg, 3, 1.0)
        assert frame.source_kind == SourceKind.SYNTHETIC
        assert frame.source_id == "test:synth"
        assert frame.vfo_index == 3
        assert frame.frequency_hz == 400e6
        assert frame.station_id == "SYNTH"
        assert 0.0 <= frame.confidence <= 1.0
        assert frame.antenna_type == "UCA"

    def test_noise_floor_respected(self):
        src = self._make_source(noise_floor_dbm=-80.0)
        cfg = SyntheticSignalConfig(bearing_deg=90.0, power_dbm=-30.0)
        frame = src._generate_frame(cfg, 0, 0.0)
        # All values should be in [-100, 0] dB range after normalization
        assert np.all(frame.doa_array >= -100.0)
        assert np.all(frame.doa_array <= 0.0)

    def test_multi_signal_different_vfos(self):
        signals = [
            SyntheticSignalConfig(bearing_deg=45.0),
            SyntheticSignalConfig(bearing_deg=200.0),
        ]
        src = self._make_source(signals=signals)
        frames = [src._generate_frame(sig, i, 0.0) for i, sig in enumerate(signals)]
        assert frames[0].vfo_index == 0
        assert frames[1].vfo_index == 1
        assert abs(frames[0].bearing_deg - 45.0) < 2
        assert abs(frames[1].bearing_deg - 200.0) < 2

    def test_bearing_drift_linear(self):
        cfg = SyntheticSignalConfig(bearing_deg=90.0, drift_rate_deg_per_sec=10.0)
        src = self._make_source()
        # At t=0 bearing should be 90
        b0 = src._current_bearing(cfg, 0.0)
        assert abs(b0 - 90.0) < 0.01
        # At t=1 bearing should be 100
        b1 = src._current_bearing(cfg, 1.0)
        assert abs(b1 - 100.0) < 0.01
        # At t=27 bearing should wrap: 90 + 270 = 360 -> 0
        b27 = src._current_bearing(cfg, 27.0)
        assert abs(b27 - 0.0) < 0.01

    def test_bearing_drift_sinusoidal(self):
        cfg = SyntheticSignalConfig(
            bearing_deg=180.0,
            drift_amplitude_deg=20.0,
            drift_period_sec=4.0,
        )
        src = self._make_source()
        b0 = src._current_bearing(cfg, 0.0)
        assert abs(b0 - 180.0) < 0.01
        # At t=1 (quarter period), sin = 1 -> bearing = 200
        b1 = src._current_bearing(cfg, 1.0)
        assert abs(b1 - 200.0) < 0.5
