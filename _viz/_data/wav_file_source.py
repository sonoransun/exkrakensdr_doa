from __future__ import annotations

import re
import time
from pathlib import Path

import numpy as np
from scipy.io import wavfile

from ..constants import SourceKind
from .base_source import BaseSource
from .data_frame import DOA_ARRAY_SIZE, DoAFrame

# Filename pattern: {datetime},FM_{freq}MHz,DOA_{bearing}.wav
WAV_FILENAME_RE = re.compile(r".*,FM_(?P<freq_mhz>[\d.]+)MHz(?:,DOA_(?P<bearing>[\d._]+))?\.wav$")


class WavFileSource(BaseSource):
    """Replays WAV files as spectrograms. WAV files contain demodulated audio only,
    so DoA data is static (parsed from filename). Spectrum is computed via STFT.
    """

    def __init__(
        self,
        file_path: str,
        source_id: str | None = None,
        chunk_samples: int = 4096,
        parent=None,
    ):
        self._file_path = Path(file_path)
        if source_id is None:
            source_id = f"file:{self._file_path.name}"
        super().__init__(source_id=source_id, parent=parent)

        self._chunk_samples = chunk_samples
        self._playback_speed = 1.0
        self._seek_position: float | None = None
        self._center_freq_hz = 0.0
        self._static_bearing = 0.0

        # Parse metadata from filename
        match = WAV_FILENAME_RE.match(str(self._file_path))
        if match:
            self._center_freq_hz = float(match.group("freq_mhz")) * 1e6
            bearing_str = match.group("bearing")
            if bearing_str:
                self._static_bearing = float(bearing_str.replace("_", "."))

    @property
    def is_seekable(self) -> bool:
        return True

    @property
    def duration_ms(self) -> int | None:
        try:
            sr, data = wavfile.read(str(self._file_path), mmap=True)
            if data.ndim > 1:
                data = data[:, 0]
            return int(len(data) / sr * 1000)
        except Exception:
            return None

    def seek(self, position: float):
        self._seek_position = max(0.0, min(1.0, position))

    def set_playback_speed(self, speed: float):
        self._playback_speed = max(0.0, speed)

    def _run_loop(self):
        sr, data = wavfile.read(str(self._file_path))
        if data.ndim > 1:
            data = data[:, 0]  # mono
        data = data.astype(np.float32) / 32768.0  # normalize int16

        total_samples = len(data)
        total_chunks = total_samples // self._chunk_samples
        if total_chunks == 0:
            return

        chunk_duration_ms = (self._chunk_samples / sr) * 1000
        current_chunk = 0

        while current_chunk < total_chunks and not self._stop_requested:
            while self._pause_requested and not self._stop_requested:
                self.msleep(50)
            if self._stop_requested:
                break

            if self._seek_position is not None:
                current_chunk = int(self._seek_position * (total_chunks - 1))
                self._seek_position = None

            start = current_chunk * self._chunk_samples
            chunk = data[start : start + self._chunk_samples]

            # Compute spectrum via FFT
            nfft = len(chunk)
            spectrum = np.fft.rfft(chunk * np.hanning(nfft))
            power_db = (20.0 * np.log10(np.abs(spectrum) + 1e-20)).astype(np.float32)
            freq_axis = (np.fft.rfftfreq(nfft, 1.0 / sr) + self._center_freq_hz).astype(np.float32)

            position = current_chunk / max(total_chunks - 1, 1)

            # Build a static DoA array with a peak at the filename bearing
            doa_array = np.full(DOA_ARRAY_SIZE, -80.0, dtype=np.float32)
            if self._static_bearing >= 0:
                idx = int(self._static_bearing) % DOA_ARRAY_SIZE
                for offset in range(-5, 6):
                    i = (idx + offset) % DOA_ARRAY_SIZE
                    doa_array[i] = -80.0 + 80.0 * np.exp(-0.5 * (offset / 2.0) ** 2)

            frame = DoAFrame(
                source_id=self._source_id,
                source_kind=SourceKind.FILE_WAV,
                timestamp_ms=int(time.time() * 1000),
                frequency_hz=self._center_freq_hz,
                bearing_deg=self._static_bearing,
                doa_array=doa_array,
                confidence=0.0,
                power_dbm=float(np.max(power_db)),
                station_id="WAV_FILE",
                antenna_type="UCA",
                spectrum_freqs=freq_axis,
                spectrum_power_db=power_db,
                file_position=position,
            )
            self._emit_frame(frame)
            self.progress_changed.emit(position)

            if self._playback_speed > 0:
                sleep_ms = chunk_duration_ms / self._playback_speed
                self.msleep(int(min(sleep_ms, 5000)))

            current_chunk += 1
