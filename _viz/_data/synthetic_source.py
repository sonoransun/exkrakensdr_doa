from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from ..constants import SourceKind
from .base_source import BaseSource
from .data_frame import DOA_ARRAY_SIZE, DoAFrame


@dataclass
class SyntheticSignalConfig:
    """Configuration for one simulated signal source."""

    bearing_deg: float = 90.0
    power_dbm: float = -30.0
    frequency_hz: float = 394.3e6
    drift_rate_deg_per_sec: float = 0.0  # linear bearing drift
    drift_amplitude_deg: float = 0.0  # sinusoidal bearing oscillation
    drift_period_sec: float = 10.0


class SyntheticSource(BaseSource):
    """Generates configurable synthetic DoA data for testing.

    Fast mode: directly synthesizes Gaussian peaks in the DoA array.
    Sub-millisecond per frame, no IQ or DSP required.
    """

    def __init__(
        self,
        source_id: str = "synth:0",
        signals: list[SyntheticSignalConfig] | None = None,
        noise_floor_dbm: float = -80.0,
        antenna_type: str = "UCA",
        frame_rate_hz: float = 10.0,
        parent=None,
    ):
        super().__init__(source_id=source_id, parent=parent)
        self._signals = signals or [SyntheticSignalConfig()]
        self._noise_floor_dbm = noise_floor_dbm
        self._antenna_type = antenna_type
        self._frame_rate_hz = frame_rate_hz

    @property
    def signals(self) -> list[SyntheticSignalConfig]:
        return self._signals

    def _run_loop(self):
        frame_interval_ms = int(1000.0 / self._frame_rate_hz)
        start_time = time.time()

        while not self._stop_requested:
            while self._pause_requested and not self._stop_requested:
                self.msleep(50)
            if self._stop_requested:
                break

            elapsed = time.time() - start_time

            for vfo_idx, sig_cfg in enumerate(self._signals):
                frame = self._generate_frame(sig_cfg, vfo_idx, elapsed)
                self._emit_frame(frame)

            self.msleep(frame_interval_ms)

    def _generate_frame(self, cfg: SyntheticSignalConfig, vfo_index: int, elapsed: float) -> DoAFrame:
        bearing = self._current_bearing(cfg, elapsed)
        thetas = np.arange(DOA_ARRAY_SIZE, dtype=np.float32)

        # Angular distance accounting for wrap-around
        diff = np.minimum(np.abs(thetas - bearing), DOA_ARRAY_SIZE - np.abs(thetas - bearing))

        # Gaussian peak with ~10 degree spread
        peak_linear = np.exp(-0.5 * (diff / 5.0) ** 2)
        noise_linear = 10 ** (self._noise_floor_dbm / 10.0)
        signal_linear = 10 ** (cfg.power_dbm / 10.0)

        doa_raw = peak_linear * signal_linear + noise_linear
        doa_db = 10.0 * np.log10(doa_raw + 1e-20)

        # Normalize like DOA_plot_util: shift min to 0, scale, then log
        doa_db -= np.min(doa_db)
        max_val = np.max(doa_db)
        if max_val > 0:
            doa_normalized = doa_db / max_val
        else:
            doa_normalized = doa_db
        doa_result = 10.0 * np.log10(doa_normalized + 1e-15)
        doa_result = np.clip(doa_result, -100, 0).astype(np.float32)

        confidence = 0.85 + np.random.uniform(-0.05, 0.05)
        power = cfg.power_dbm + np.random.uniform(-1, 1)
        snr = cfg.power_dbm - self._noise_floor_dbm + np.random.uniform(-2, 2)

        return DoAFrame(
            source_id=self._source_id,
            source_kind=SourceKind.SYNTHETIC,
            timestamp_ms=int(time.time() * 1000),
            vfo_index=vfo_index,
            frequency_hz=cfg.frequency_hz,
            bearing_deg=bearing,
            doa_array=doa_result,
            confidence=max(0.0, min(1.0, confidence)),
            power_dbm=power,
            snr_db=snr,
            station_id="SYNTH",
            antenna_type=self._antenna_type,
        )

    def _current_bearing(self, cfg: SyntheticSignalConfig, elapsed: float) -> float:
        bearing = cfg.bearing_deg
        bearing += cfg.drift_rate_deg_per_sec * elapsed
        if cfg.drift_amplitude_deg > 0 and cfg.drift_period_sec > 0:
            bearing += cfg.drift_amplitude_deg * math.sin(2 * math.pi * elapsed / cfg.drift_period_sec)
        return bearing % DOA_ARRAY_SIZE
