import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from _viz._data.csv_file_source import CsvFileSource
from _viz._data.data_frame import DOA_ARRAY_SIZE
from _viz.constants import SourceKind

FIXTURES = os.path.join(os.path.dirname(__file__), "fixtures")
CSV_PATH = os.path.join(FIXTURES, "sample_3rows.csv")


class TestCsvFileSource:
    def test_parse_row(self):
        src = CsvFileSource(CSV_PATH)
        # Pre-load rows
        import csv

        with open(CSV_PATH) as f:
            rows = list(csv.reader(f))

        frame = src._parse_row(rows[0], 0.0)
        assert frame is not None
        assert frame.source_kind == SourceKind.FILE_CSV
        assert frame.bearing_deg == 45.0
        assert frame.confidence == 0.9
        assert frame.power_dbm == -30.0
        assert frame.frequency_hz == 394317376.0
        assert frame.station_id == "TEST01"
        assert frame.latitude == 50.8
        assert frame.longitude == 6.9
        assert frame.antenna_type == "UCA"
        assert frame.doa_array.shape == (DOA_ARRAY_SIZE,)

    def test_doa_array_has_peak_at_bearing(self):
        src = CsvFileSource(CSV_PATH)
        import csv

        with open(CSV_PATH) as f:
            rows = list(csv.reader(f))

        frame = src._parse_row(rows[0], 0.0)
        peak_idx = int(np.argmax(frame.doa_array))
        assert abs(peak_idx - 45) <= 2

    def test_seekable(self):
        src = CsvFileSource(CSV_PATH)
        assert src.is_seekable is True

    def test_multiple_rows_different_bearings(self):
        src = CsvFileSource(CSV_PATH)
        import csv

        with open(CSV_PATH) as f:
            rows = list(csv.reader(f))

        frames = [src._parse_row(row, i / 2.0) for i, row in enumerate(rows)]
        assert all(f is not None for f in frames)
        assert frames[0].bearing_deg == 45.0
        assert frames[1].bearing_deg == 47.0
        assert frames[2].bearing_deg == 50.0

    def test_file_position_set(self):
        src = CsvFileSource(CSV_PATH)
        import csv

        with open(CSV_PATH) as f:
            rows = list(csv.reader(f))

        frame = src._parse_row(rows[1], 0.5)
        assert frame.file_position == 0.5

    def test_source_id_from_filename(self):
        src = CsvFileSource(CSV_PATH)
        assert "sample_3rows.csv" in src.source_id
