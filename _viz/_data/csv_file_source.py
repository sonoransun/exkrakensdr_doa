from __future__ import annotations

import csv
from pathlib import Path

import numpy as np

from ..constants import SourceKind
from .base_source import BaseSource
from .data_frame import DOA_ARRAY_SIZE, DoAFrame

# CSV column layout (from kraken_sdr_signal_processor.py:809):
# 0: timestamp, 1: bearing(360-theta), 2: confidence, 3: power, 4: freq,
# 5: ant_type, 6: latency, 7: station_id, 8: lat, 9: lon,
# 10: heading, 11: heading2, 12: GPS, 13-16: R,R,R,R
# 17+: doa_array[0..359]
DOA_START_COL = 17


class CsvFileSource(BaseSource):
    """Replays a KrakenSDR CSV log file at original timing (adjustable speed)."""

    def __init__(self, file_path: str, source_id: str | None = None, parent=None):
        self._file_path = Path(file_path)
        if source_id is None:
            source_id = f"file:{self._file_path.name}"
        super().__init__(source_id=source_id, parent=parent)

        self._playback_speed = 1.0
        self._seek_position: float | None = None
        self._rows: list[list[str]] = []
        self._current_index = 0

    @property
    def is_seekable(self) -> bool:
        return True

    @property
    def duration_ms(self) -> int | None:
        if len(self._rows) >= 2:
            try:
                first_ts = int(self._rows[0][0].strip())
                last_ts = int(self._rows[-1][0].strip())
                return last_ts - first_ts
            except (ValueError, IndexError):
                return None
        return None

    def seek(self, position: float):
        self._seek_position = max(0.0, min(1.0, position))

    def set_playback_speed(self, speed: float):
        self._playback_speed = max(0.0, speed)

    def _run_loop(self):
        with open(self._file_path, "r") as f:
            reader = csv.reader(f)
            self._rows = [row for row in reader if row and row[0].strip()]

        if not self._rows:
            return

        total = len(self._rows)
        self._current_index = 0
        prev_ts = None

        while self._current_index < total and not self._stop_requested:
            while self._pause_requested and not self._stop_requested:
                self.msleep(50)
            if self._stop_requested:
                break

            if self._seek_position is not None:
                self._current_index = int(self._seek_position * (total - 1))
                self._seek_position = None
                prev_ts = None

            row = self._rows[self._current_index]
            position = self._current_index / max(total - 1, 1)
            frame = self._parse_row(row, position)

            if frame is not None:
                current_ts = frame.timestamp_ms
                if prev_ts is not None and self._playback_speed > 0:
                    delta_ms = current_ts - prev_ts
                    sleep_ms = delta_ms / self._playback_speed
                    if sleep_ms > 0:
                        self.msleep(int(min(sleep_ms, 5000)))
                prev_ts = current_ts

                self._emit_frame(frame)
                self.progress_changed.emit(position)

            self._current_index += 1

    def _parse_row(self, row: list[str], position: float) -> DoAFrame | None:
        try:
            timestamp_ms = int(row[0].strip())
            bearing = float(row[1].strip())
            confidence = float(row[2].strip())
            power = float(row[3].strip())
            freq = float(row[4].strip())
            ant_type = row[5].strip()
            _ = int(row[6].strip())  # latency (parsed but unused)
            station_id = row[7].strip()
            lat = float(row[8].strip())
            lon = float(row[9].strip())

            # Parse DoA array (starts at column 17)
            doa_values = []
            for v in row[DOA_START_COL : DOA_START_COL + DOA_ARRAY_SIZE]:
                v = v.strip()
                if v:
                    doa_values.append(float(v))
            doa_array = np.array(doa_values, dtype=np.float32)
            if doa_array.size < DOA_ARRAY_SIZE:
                doa_array = np.pad(doa_array, (0, DOA_ARRAY_SIZE - doa_array.size))
            elif doa_array.size > DOA_ARRAY_SIZE:
                doa_array = doa_array[:DOA_ARRAY_SIZE]

            return DoAFrame(
                source_id=self._source_id,
                source_kind=SourceKind.FILE_CSV,
                timestamp_ms=timestamp_ms,
                frequency_hz=freq,
                bearing_deg=bearing,
                doa_array=doa_array,
                confidence=confidence,
                power_dbm=power,
                station_id=station_id,
                latitude=lat,
                longitude=lon,
                antenna_type=ant_type,
                file_position=position,
            )
        except (IndexError, ValueError):
            return None
