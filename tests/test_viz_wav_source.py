import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _viz._data.wav_file_source import WAV_FILENAME_RE, WavFileSource

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
WAV_NAMED = os.path.join(FIXTURES, "01-Jan-2025_00h00m00s,FM_394.317MHz,DOA_45.0.wav")
WAV_PLAIN = os.path.join(FIXTURES, "sample_1sec.wav")


class TestWavFilenameRegex:
    def test_matches_standard_format(self):
        m = WAV_FILENAME_RE.match("01-Jan-2025_00h00m00s,FM_394.317MHz,DOA_45.0.wav")
        assert m is not None
        assert m.group("freq_mhz") == "394.317"
        assert m.group("bearing") == "45.0"

    def test_no_match_on_other_extension(self):
        m = WAV_FILENAME_RE.match("test.iq")
        assert m is None


class TestWavFileSource:
    def test_seekable(self):
        src = WavFileSource(WAV_PLAIN)
        assert src.is_seekable is True

    def test_duration_ms(self):
        src = WavFileSource(WAV_PLAIN)
        dur = src.duration_ms
        # 1 second of audio -> ~1000ms
        assert dur is not None
        assert 900 <= dur <= 1100

    def test_parses_freq_from_filename(self):
        src = WavFileSource(WAV_NAMED)
        assert abs(src._center_freq_hz - 394.317e6) < 1.0

    def test_parses_bearing_from_filename(self):
        src = WavFileSource(WAV_NAMED)
        assert src._static_bearing == 45.0

    def test_source_id_from_filename(self):
        src = WavFileSource(WAV_NAMED)
        assert "FM_394.317MHz" in src.source_id
