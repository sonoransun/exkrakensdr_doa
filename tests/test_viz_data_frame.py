import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _viz._data.data_frame import DOA_ARRAY_SIZE, DoAFrame, SpectrumFrame
from _viz.constants import SourceKind


class TestDoAFrame:
    def test_default_construction(self):
        frame = DoAFrame(source_id="test", source_kind=SourceKind.SYNTHETIC, timestamp_ms=1000)
        assert frame.source_id == "test"
        assert frame.source_kind == SourceKind.SYNTHETIC
        assert frame.timestamp_ms == 1000
        assert frame.vfo_index == 0
        assert frame.frequency_hz == 0.0
        assert frame.bearing_deg == 0.0
        assert frame.confidence == 0.0
        assert frame.power_dbm == -120.0
        assert frame.snr_db == 0.0
        assert frame.station_id == ""
        assert frame.latitude == 0.0
        assert frame.longitude == 0.0
        assert frame.antenna_type == "UCA"
        assert frame.spectrum_freqs is None
        assert frame.spectrum_power_db is None
        assert frame.file_position == 0.0

    def test_doa_array_shape(self):
        frame = DoAFrame(source_id="test", source_kind=SourceKind.LIVE_WS, timestamp_ms=0)
        assert frame.doa_array.shape == (DOA_ARRAY_SIZE,)
        assert frame.doa_array.dtype == np.float32

    def test_doa_array_default_is_zeros(self):
        frame = DoAFrame(source_id="test", source_kind=SourceKind.LIVE_WS, timestamp_ms=0)
        assert np.all(frame.doa_array == 0)

    def test_doa_array_not_shared_between_instances(self):
        f1 = DoAFrame(source_id="a", source_kind=SourceKind.SYNTHETIC, timestamp_ms=0)
        f2 = DoAFrame(source_id="b", source_kind=SourceKind.SYNTHETIC, timestamp_ms=0)
        f1.doa_array[0] = 99.0
        assert f2.doa_array[0] == 0.0

    def test_custom_doa_array(self):
        custom = np.arange(360, dtype=np.float32)
        frame = DoAFrame(
            source_id="test",
            source_kind=SourceKind.FILE_CSV,
            timestamp_ms=500,
            doa_array=custom,
            bearing_deg=45.0,
            confidence=0.95,
            power_dbm=-30.0,
        )
        assert np.array_equal(frame.doa_array, custom)
        assert frame.bearing_deg == 45.0
        assert frame.confidence == 0.95

    def test_all_source_kinds(self):
        for kind in SourceKind:
            frame = DoAFrame(source_id="test", source_kind=kind, timestamp_ms=0)
            assert frame.source_kind == kind

    def test_spectrum_fields(self):
        freqs = np.linspace(390e6, 400e6, 1024, dtype=np.float32)
        power = np.random.randn(1024).astype(np.float32)
        frame = DoAFrame(
            source_id="test",
            source_kind=SourceKind.FILE_IQ,
            timestamp_ms=0,
            spectrum_freqs=freqs,
            spectrum_power_db=power,
        )
        assert frame.spectrum_freqs is not None
        assert frame.spectrum_power_db is not None
        assert frame.spectrum_freqs.shape == (1024,)


class TestSpectrumFrame:
    def test_default_construction(self):
        frame = SpectrumFrame(source_id="test", source_kind=SourceKind.FILE_WAV, timestamp_ms=0)
        assert frame.freq_axis_hz.shape == (0,)
        assert frame.power_db.shape == (0,)
        assert frame.center_freq_hz == 0.0
        assert frame.file_position == 0.0

    def test_with_data(self):
        freqs = np.linspace(0, 24000, 4096, dtype=np.float32)
        power = np.random.randn(4096).astype(np.float32)
        frame = SpectrumFrame(
            source_id="wav:test.wav",
            source_kind=SourceKind.FILE_WAV,
            timestamp_ms=12345,
            freq_axis_hz=freqs,
            power_db=power,
            center_freq_hz=394e6,
            file_position=0.5,
        )
        assert frame.freq_axis_hz.shape == (4096,)
        assert frame.file_position == 0.5
