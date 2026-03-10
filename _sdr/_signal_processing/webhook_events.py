"""Webhook event detection module for SDR signal processing.

Detects signal events (appearance, disappearance, novel frequencies, DoA changes,
power alerts) and produces structured webhook event payloads.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

import logging

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of webhook events that can be emitted."""

    SIGNAL_APPEAR = "signal_appear"
    SIGNAL_DISAPPEAR = "signal_disappear"
    NOVEL_FREQUENCY = "novel_frequency"
    DOA_CHANGE = "doa_change"
    POWER_ALERT = "power_alert"


@dataclass
class WebhookEvent:
    """Structured webhook event payload.

    Required fields describe the core event; optional fields carry event-specific
    details and are omitted from the serialised dict when they are None.
    """

    event_type: str
    timestamp: int  # epoch milliseconds
    vfo_index: int
    frequency_hz: float
    station_id: str
    latitude: float
    longitude: float

    # Optional event-specific fields
    bearing_deg: Optional[float] = None
    confidence: Optional[float] = None
    power_dbm: Optional[float] = None
    snr_db: Optional[float] = None
    previous_bearing_deg: Optional[float] = None
    bearing_change_deg: Optional[float] = None
    power_threshold_crossed: Optional[str] = None  # "high" / "low"
    novelty_method: Optional[str] = None  # "allowlist" / "autolearn" / "both"

    def to_dict(self) -> Dict[str, object]:
        """Return a dictionary representation, filtering out ``None`` values."""
        return {k: v for k, v in self.__dict__.items() if v is not None}


class FrequencyHistory:
    """Auto-learning novelty detection based on a sliding time window.

    Frequencies are *canonicalised* (snapped to the nearest tolerance bucket)
    before being stored or queried so that minor frequency drift does not
    produce spurious novelty detections.
    """

    def __init__(self, window_sec: float = 3600.0, tolerance_hz: float = 5000.0) -> None:
        self.window_sec: float = window_sec
        self.tolerance_hz: float = tolerance_hz
        # Mapping from canonical frequency (float) to the most recent observation
        # timestamp (seconds, monotonic or wall-clock).
        self._seen: Dict[float, float] = {}

    def record(self, freq_hz: float) -> None:
        """Record an observation of *freq_hz* at the current time."""
        canonical = self._canonicalize(freq_hz)
        self._seen[canonical] = time.time()

    def is_novel(self, freq_hz: float) -> bool:
        """Return ``True`` if *freq_hz* has not been observed within the time window."""
        self._prune()
        canonical = self._canonicalize(freq_hz)
        return canonical not in self._seen

    def _canonicalize(self, freq_hz: float) -> float:
        """Snap *freq_hz* to the nearest tolerance bucket."""
        if self.tolerance_hz <= 0:
            return freq_hz
        return round(freq_hz / self.tolerance_hz) * self.tolerance_hz

    def _prune(self) -> None:
        """Remove entries older than the configured window."""
        cutoff = time.time() - self.window_sec
        expired = [f for f, ts in self._seen.items() if ts < cutoff]
        for f in expired:
            del self._seen[f]


@dataclass
class VFOSignalState:
    """Per-VFO tracking state used by the event detector."""

    signal_active: bool = False
    last_bearing: Optional[float] = None
    last_power: Optional[float] = None
    power_alert_state: Optional[str] = None  # None | "high" | "low"


class WebhookEventDetector:
    """Main event detector – examines incoming signal data and emits webhook events.

    Internally maintains per-VFO state, a frequency novelty history, and a
    pending-event queue that consumers drain via :meth:`drain_events`.
    """

    def __init__(self, max_vfos: int = 16) -> None:
        # Per-VFO state
        self.vfo_states: List[VFOSignalState] = [VFOSignalState() for _ in range(max_vfos)]

        # Frequency novelty
        self.frequency_history: FrequencyHistory = FrequencyHistory()

        # --- Configuration fields ---
        self.enabled: bool = False

        # Individual event toggles
        self.evt_signal_appear: bool = True
        self.evt_signal_disappear: bool = True
        self.evt_novel_freq: bool = True
        self.evt_doa_change: bool = True
        self.evt_power_alert: bool = True

        # DoA change threshold
        self.doa_change_threshold_deg: float = 10.0

        # Power alert thresholds
        self.power_high_threshold_dbm: float = -30.0
        self.power_low_threshold_dbm: float = -90.0

        # Allowlist-based novelty detection
        self.known_frequencies: List[float] = []
        self.freq_tolerance_hz: float = 5000.0

        # Auto-learn novelty detection
        self.autolearn_enabled: bool = False
        self.autolearn_window_sec: float = 3600.0

        # Pending event queue
        self.pending_events: List[WebhookEvent] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on_signal_detected(
        self,
        vfo_idx: int,
        freq_hz: float,
        bearing_deg: Optional[float],
        confidence: Optional[float],
        power_dbm: Optional[float],
        snr_db: Optional[float],
        station_id: str,
        lat: float,
        lon: float,
        timestamp_ms: int,
    ) -> None:
        """Process an incoming signal detection for a given VFO.

        Checks, in order:
        1. Signal appearance (and, on first appearance, frequency novelty)
        2. DoA (bearing) change beyond threshold
        3. Power alert hysteresis crossings
        """
        if not self.enabled:
            return

        if not (0 <= vfo_idx < len(self.vfo_states)):
            return

        state = self.vfo_states[vfo_idx]

        # -- 1. Signal Appearance ------------------------------------------
        if not state.signal_active:
            state.signal_active = True
            logger.debug("VFO-%d signal appeared at %.1f Hz", vfo_idx, freq_hz)

            if self.evt_signal_appear:
                self.pending_events.append(
                    WebhookEvent(
                        event_type=EventType.SIGNAL_APPEAR.value,
                        timestamp=timestamp_ms,
                        vfo_index=vfo_idx,
                        frequency_hz=freq_hz,
                        station_id=station_id,
                        latitude=lat,
                        longitude=lon,
                        bearing_deg=bearing_deg,
                        confidence=confidence,
                        power_dbm=power_dbm,
                        snr_db=snr_db,
                    )
                )

            # -- 2. Novel Frequency (only on appearance) -------------------
            if self.evt_novel_freq:
                novel_allowlist = not self._in_allowlist(freq_hz) if self.known_frequencies else False
                novel_autolearn = (
                    self.frequency_history.is_novel(freq_hz) if self.autolearn_enabled else False
                )

                if novel_allowlist or novel_autolearn:
                    if novel_allowlist and novel_autolearn:
                        method = "both"
                    elif novel_allowlist:
                        method = "allowlist"
                    else:
                        method = "autolearn"

                    self.pending_events.append(
                        WebhookEvent(
                            event_type=EventType.NOVEL_FREQUENCY.value,
                            timestamp=timestamp_ms,
                            vfo_index=vfo_idx,
                            frequency_hz=freq_hz,
                            station_id=station_id,
                            latitude=lat,
                            longitude=lon,
                            bearing_deg=bearing_deg,
                            confidence=confidence,
                            power_dbm=power_dbm,
                            snr_db=snr_db,
                            novelty_method=method,
                        )
                    )

                # Always record in auto-learn history (even if not novel) so
                # the window stays up to date.
                if self.autolearn_enabled:
                    self.frequency_history.record(freq_hz)

        # -- 3. DoA Change -------------------------------------------------
        if self.evt_doa_change and bearing_deg is not None and state.last_bearing is not None:
            delta = abs(bearing_deg - state.last_bearing)
            delta = min(delta, 360.0 - delta)
            if delta > self.doa_change_threshold_deg:
                self.pending_events.append(
                    WebhookEvent(
                        event_type=EventType.DOA_CHANGE.value,
                        timestamp=timestamp_ms,
                        vfo_index=vfo_idx,
                        frequency_hz=freq_hz,
                        station_id=station_id,
                        latitude=lat,
                        longitude=lon,
                        bearing_deg=bearing_deg,
                        confidence=confidence,
                        power_dbm=power_dbm,
                        snr_db=snr_db,
                        previous_bearing_deg=state.last_bearing,
                        bearing_change_deg=delta,
                    )
                )

        # -- 4. Power Alert (hysteresis state machine) ---------------------
        if self.evt_power_alert and power_dbm is not None:
            self._check_power_alert(state, power_dbm, vfo_idx, freq_hz, station_id, lat, lon, timestamp_ms)

        # -- 5. Update state -----------------------------------------------
        if bearing_deg is not None:
            state.last_bearing = bearing_deg
        if power_dbm is not None:
            state.last_power = power_dbm

    def on_signal_lost(
        self,
        vfo_idx: int,
        freq_hz: float,
        station_id: str,
        lat: float,
        lon: float,
        timestamp_ms: int,
    ) -> None:
        """Process a signal-lost notification for a given VFO."""
        if not self.enabled:
            return

        if not (0 <= vfo_idx < len(self.vfo_states)):
            return

        state = self.vfo_states[vfo_idx]

        if state.signal_active:
            if self.evt_signal_disappear:
                self.pending_events.append(
                    WebhookEvent(
                        event_type=EventType.SIGNAL_DISAPPEAR.value,
                        timestamp=timestamp_ms,
                        vfo_index=vfo_idx,
                        frequency_hz=freq_hz,
                        station_id=station_id,
                        latitude=lat,
                        longitude=lon,
                    )
                )

            state.signal_active = False
            logger.debug("VFO-%d signal lost", vfo_idx)
            state.last_bearing = None
            state.last_power = None
            state.power_alert_state = None

    def drain_events(self) -> List[WebhookEvent]:
        """Return all pending events and clear the internal queue."""
        events = self.pending_events
        if events:
            logger.debug("Drained %d webhook events", len(events))
        self.pending_events = []
        return events

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _in_allowlist(self, freq_hz: float) -> bool:
        """Return ``True`` if *freq_hz* is within tolerance of any known frequency."""
        for known in self.known_frequencies:
            if abs(freq_hz - known) <= self.freq_tolerance_hz:
                return True
        return False

    def _check_power_alert(
        self,
        state: VFOSignalState,
        power_dbm: float,
        vfo_idx: int,
        freq_hz: float,
        station_id: str,
        lat: float,
        lon: float,
        timestamp_ms: int,
    ) -> None:
        """Hysteresis-based power alert state machine.

        Transitions:
        - None  -> "high"  when power >= high threshold
        - None  -> "low"   when power <= low threshold
        - "high" -> None   when power drops below high threshold
        - "low"  -> None   when power rises above low threshold
        """
        current = state.power_alert_state

        if current is None:
            if power_dbm >= self.power_high_threshold_dbm:
                state.power_alert_state = "high"
                self.pending_events.append(
                    WebhookEvent(
                        event_type=EventType.POWER_ALERT.value,
                        timestamp=timestamp_ms,
                        vfo_index=vfo_idx,
                        frequency_hz=freq_hz,
                        station_id=station_id,
                        latitude=lat,
                        longitude=lon,
                        power_dbm=power_dbm,
                        power_threshold_crossed="high",
                    )
                )
            elif power_dbm <= self.power_low_threshold_dbm:
                state.power_alert_state = "low"
                self.pending_events.append(
                    WebhookEvent(
                        event_type=EventType.POWER_ALERT.value,
                        timestamp=timestamp_ms,
                        vfo_index=vfo_idx,
                        frequency_hz=freq_hz,
                        station_id=station_id,
                        latitude=lat,
                        longitude=lon,
                        power_dbm=power_dbm,
                        power_threshold_crossed="low",
                    )
                )
        elif current == "high":
            if power_dbm < self.power_high_threshold_dbm:
                state.power_alert_state = None
        elif current == "low":
            if power_dbm > self.power_low_threshold_dbm:
                state.power_alert_state = None
