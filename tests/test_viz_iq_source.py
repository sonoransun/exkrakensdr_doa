import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _viz._data.iq_file_source import IQ_FILENAME_RE, IqFileSource

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
IQ_NAMED = os.path.join(FIXTURES, "01-Jan-2025_00h00m00s,IQ_394.317MHz,DOA_45.0.iq")
IQ_PLAIN = os.path.join(FIXTURES, "sample_100samples.iq")


class TestIqFilenameRegex:
    def test_matches_standard_format(self):
        m = IQ_FILENAME_RE.match("01-Jan-2025_00h00m00s,IQ_394.317MHz,DOA_45.0.iq")
        assert m is not None
        assert m.group("freq_mhz") == "394.317"
        assert m.group("bearing") == "45.0"

    def test_matches_without_doa(self):
        m = IQ_FILENAME_RE.match("01-Jan-2025_00h00m00s,IQ_394.317MHz.iq")
        assert m is not None
        assert m.group("freq_mhz") == "394.317"

    def test_no_match_on_other_extension(self):
        m = IQ_FILENAME_RE.match("test.csv")
        assert m is None


class TestIqFileSource:
    def test_seekable(self):
        src = IqFileSource(IQ_PLAIN, n_channels=5, sampling_freq=2.4e6, center_freq_hz=394e6)
        assert src.is_seekable is True

    def test_duration_ms(self):
        src = IqFileSource(IQ_PLAIN, n_channels=5, sampling_freq=2.4e6)
        dur = src.duration_ms
        # 100 samples / 2.4e6 = 0.0000417 sec = 0.0417 ms -> ~0
        assert dur is not None
        assert dur >= 0

    def test_parses_freq_from_filename(self):
        src = IqFileSource(IQ_NAMED, n_channels=5, sampling_freq=2.4e6)
        assert abs(src._center_freq_hz - 394.317e6) < 1.0

    def test_source_id_from_filename(self):
        src = IqFileSource(IQ_NAMED)
        assert "IQ_394.317MHz" in src.source_id

    def test_explicit_center_freq_overrides(self):
        src = IqFileSource(IQ_NAMED, center_freq_hz=400e6)
        assert src._center_freq_hz == 400e6
