from __future__ import annotations

import re
import time
from pathlib import Path

import numpy as np
from scipy import fft
from scipy import signal as scipy_signal

from ..constants import SourceKind
from .base_source import BaseSource
from .data_frame import DOA_ARRAY_SIZE, DoAFrame

# Filename pattern: {datetime},IQ_{freq}MHz,DOA_{bearing}.iq
IQ_FILENAME_RE = re.compile(r".*,IQ_(?P<freq_mhz>[\d.]+)MHz(?:,DOA_(?P<bearing>[\d._]+))?\.iq$")

SAMPLE_SIZE = 8  # complex64 = 4 + 4 bytes


class IqFileSource(BaseSource):
    """Replays raw IQ files through spectrum analysis and (optionally) DoA processing.

    The IQ file is raw complex64 binary with metadata in the filename.
    Spectrum is computed via Welch periodogram. DoA processing reuses
    the existing module-level functions from kraken_sdr_signal_processor.py
    if available; otherwise, only spectrum is provided.
    """

    def __init__(
        self,
        file_path: str,
        source_id: str | None = None,
        n_channels: int = 5,
        sampling_freq: float = 2.4e6,
        center_freq_hz: float = 0,
        chunk_samples: int = 65536,
        parent=None,
    ):
        self._file_path = Path(file_path)
        if source_id is None:
            source_id = f"file:{self._file_path.name}"
        super().__init__(source_id=source_id, parent=parent)

        self._n_channels = n_channels
        self._sampling_freq = sampling_freq
        self._center_freq_hz = center_freq_hz
        self._chunk_samples = chunk_samples
        self._playback_speed = 1.0
        self._seek_position: float | None = None
        self._doa_available = False

        # Parse metadata from filename
        match = IQ_FILENAME_RE.match(str(self._file_path))
        if match:
            if self._center_freq_hz == 0:
                self._center_freq_hz = float(match.group("freq_mhz")) * 1e6

    @property
    def is_seekable(self) -> bool:
        return True

    @property
    def duration_ms(self) -> int | None:
        try:
            file_size = self._file_path.stat().st_size
            total_samples = file_size // (SAMPLE_SIZE * self._n_channels)
            return int(total_samples / self._sampling_freq * 1000)
        except OSError:
            return None

    def seek(self, position: float):
        self._seek_position = max(0.0, min(1.0, position))

    def set_playback_speed(self, speed: float):
        self._playback_speed = max(0.0, speed)

    def _run_loop(self):
        # Try to import DoA processing functions
        doa_funcs = self._try_import_doa_funcs()

        file_size = self._file_path.stat().st_size
        bytes_per_chunk = self._chunk_samples * self._n_channels * SAMPLE_SIZE
        total_chunks = file_size // bytes_per_chunk
        if total_chunks == 0:
            return

        chunk_duration_ms = (self._chunk_samples / self._sampling_freq) * 1000
        current_chunk = 0

        with open(self._file_path, "rb") as f:
            while current_chunk < total_chunks and not self._stop_requested:
                while self._pause_requested and not self._stop_requested:
                    self.msleep(50)
                if self._stop_requested:
                    break

                if self._seek_position is not None:
                    current_chunk = int(self._seek_position * (total_chunks - 1))
                    f.seek(current_chunk * bytes_per_chunk)
                    self._seek_position = None

                raw = f.read(bytes_per_chunk)
                if len(raw) < bytes_per_chunk:
                    break

                iq_samples = np.frombuffer(raw, dtype=np.complex64).reshape(self._n_channels, self._chunk_samples)

                # Compute spectrum
                nfft = fft.next_fast_len(4096)
                f_axis, pxx = scipy_signal.welch(
                    iq_samples[0],
                    self._sampling_freq,
                    nperseg=min(nfft, self._chunk_samples),
                    nfft=nfft,
                    noverlap=0,
                    detrend=False,
                    return_onesided=False,
                    window="blackman",
                    scaling="spectrum",
                )
                spectrum_db = fft.fftshift(10 * np.log10(pxx + 1e-20)).astype(np.float32)
                freq_axis = (fft.fftshift(f_axis) + self._center_freq_hz).astype(np.float32)

                # Try DoA if available
                bearing = 0.0
                confidence = 0.0
                doa_array = np.zeros(DOA_ARRAY_SIZE, dtype=np.float32)
                snr = 0.0

                if doa_funcs:
                    try:
                        bearing, confidence, doa_array, snr = self._compute_doa(iq_samples, doa_funcs)
                    except Exception:
                        pass  # Fall back to spectrum-only

                position = current_chunk / max(total_chunks - 1, 1)
                max_power = float(np.max(spectrum_db))

                frame = DoAFrame(
                    source_id=self._source_id,
                    source_kind=SourceKind.FILE_IQ,
                    timestamp_ms=int(time.time() * 1000),
                    frequency_hz=self._center_freq_hz,
                    bearing_deg=bearing,
                    doa_array=doa_array,
                    confidence=confidence,
                    power_dbm=max_power,
                    snr_db=snr,
                    station_id="IQ_FILE",
                    antenna_type="UCA",
                    spectrum_freqs=freq_axis,
                    spectrum_power_db=spectrum_db,
                    file_position=position,
                )
                self._emit_frame(frame)
                self.progress_changed.emit(position)

                if self._playback_speed > 0:
                    sleep_ms = chunk_duration_ms / self._playback_speed
                    self.msleep(int(min(sleep_ms, 5000)))

                current_chunk += 1

    def _try_import_doa_funcs(self) -> dict | None:
        """Try to import the existing DSP functions from the signal processor."""
        try:
            import os
            import sys

            sp_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "_sdr",
                "_signal_processing",
            )
            if sp_path not in sys.path:
                sys.path.insert(0, sp_path)

            from kraken_sdr_signal_processor import (
                DOA_MUSIC,
                SNR,
                DOA_plot_util,
                calculate_doa_papr,
                corr_matrix,
                gen_scanning_vectors,
            )

            self._doa_available = True
            return {
                "corr_matrix": corr_matrix,
                "gen_scanning_vectors": gen_scanning_vectors,
                "DOA_MUSIC": DOA_MUSIC,
                "DOA_plot_util": DOA_plot_util,
                "calculate_doa_papr": calculate_doa_papr,
                "SNR": SNR,
            }
        except ImportError:
            self._doa_available = False
            return None

    def _compute_doa(self, iq_samples: np.ndarray, funcs: dict) -> tuple[float, float, np.ndarray, float]:
        """Run the DoA pipeline on IQ samples using existing functions."""
        R = funcs["corr_matrix"](iq_samples)
        M = R.shape[0]
        scanning_vectors = funcs["gen_scanning_vectors"](M, 0.5, "UCA", 0)
        doa_raw = funcs["DOA_MUSIC"](R, scanning_vectors, signal_dimension=1)
        doa_result_log = funcs["DOA_plot_util"](doa_raw)
        theta_0 = float(np.argmax(np.abs(doa_raw)))
        conf = float(funcs["calculate_doa_papr"](doa_raw))
        snr = float(funcs["SNR"](R))

        doa_array = np.array(doa_result_log, dtype=np.float32)
        if doa_array.size < DOA_ARRAY_SIZE:
            doa_array = np.pad(doa_array, (0, DOA_ARRAY_SIZE - doa_array.size))

        return theta_0, conf, doa_array, snr
