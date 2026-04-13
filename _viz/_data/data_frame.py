from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from ..constants import SourceKind

DOA_ARRAY_SIZE = 360


@dataclass(slots=True)
class DoAFrame:
    """Unified data frame produced by all sources. All visualization widgets consume only this type."""

    # Identity / provenance
    source_id: str
    source_kind: SourceKind
    timestamp_ms: int  # epoch millis (matches tStamp in the middleware JSON)
    vfo_index: int = 0

    # Frequency
    frequency_hz: float = 0.0

    # DoA result
    bearing_deg: float = 0.0  # peak bearing [0, 360)
    doa_array: np.ndarray = field(default_factory=lambda: np.zeros(DOA_ARRAY_SIZE, dtype=np.float32))
    confidence: float = 0.0  # 0.0 - 1.0
    power_dbm: float = -120.0
    snr_db: float = 0.0

    # Location
    station_id: str = ""
    latitude: float = 0.0
    longitude: float = 0.0
    antenna_type: str = "UCA"

    # Optional spectrum data (None when source doesn't provide it)
    spectrum_freqs: np.ndarray | None = None
    spectrum_power_db: np.ndarray | None = None

    # Playback metadata (file sources only)
    file_position: float = 0.0  # 0.0 to 1.0 progress through file


@dataclass(slots=True)
class SpectrumFrame:
    """Spectrum-only frame for sources that produce spectrum data without DoA (e.g. WAV)."""

    source_id: str
    source_kind: SourceKind
    timestamp_ms: int
    freq_axis_hz: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float32))
    power_db: np.ndarray = field(default_factory=lambda: np.zeros(0, dtype=np.float32))
    center_freq_hz: float = 0.0
    file_position: float = 0.0
