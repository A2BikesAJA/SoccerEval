from __future__ import annotations

"""Player visibility and screen time tracking service.

Tracks which players are visible in each frame, computes screen time
ratios, adjusts for expected off-screen time based on formation and
position, and identifies high-value frames for calibration.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


# Pitch zones for visibility tracking (3x3 grid).
PITCH_ZONES = [
    "defensive_left",
    "defensive_center",
    "defensive_right",
    "midfield_left",
    "midfield_center",
    "midfield_right",
    "attacking_left",
    "attacking_center",
    "attacking_right",
]

# Expected on-screen ratios by position for a typical follow-cam.
# These are used to adjust raw screen time into estimated actual
# involvement.  A centre midfielder is expected to be on-screen more
# than a fullback.
EXPECTED_SCREEN_TIME_BY_POSITION: dict[str, float] = {
    "GK": 0.25,
    "CB": 0.40,
    "LB": 0.30,
    "RB": 0.30,
    "CDM": 0.50,
    "CM": 0.55,
    "CAM": 0.55,
    "LM": 0.35,
    "RM": 0.35,
    "LW": 0.35,
    "RW": 0.35,
    "ST": 0.45,
    "CF": 0.50,
}

# Metrics that are safe to extrapolate vs. those that are not.
EXTRAPOLATABLE_METRICS = {
    "distance_covered",
    "sprint_count",
    "avg_speed",
    "possession_touches",
    "passes_attempted",
}

NON_EXTRAPOLATABLE_METRICS = {
    "goals",
    "assists",
    "yellow_cards",
    "red_cards",
    "shots_on_target",
    "key_passes",
}


@dataclass
class FrameVisibility:
    """Visibility record for a single frame."""

    frame_index: int
    visible_player_ids: list[int] = field(default_factory=list)
    visible_pitch_zones: list[str] = field(default_factory=list)
    field_coverage_estimate: float = 0.0


@dataclass
class PlayerVisibilityRecord:
    """Aggregated visibility data for a single player."""

    player_id: int
    visible_frame_count: int = 0
    total_frame_count: int = 0
    first_seen_frame: Optional[int] = None
    last_seen_frame: Optional[int] = None
    visible_frame_indices: list[int] = field(default_factory=list)

    @property
    def screen_time_ratio(self) -> float:
        """Fraction of total frames where this player was visible."""
        if self.total_frame_count == 0:
            return 0.0
        return self.visible_frame_count / self.total_frame_count


class VisibilityTracker:
    """Tracks player visibility and screen time across a game.

    Maintains per-frame records of which players and pitch zones are
    visible, computes screen time ratios, and provides methods for
    adjusting metrics based on expected off-screen time.
    """

    def __init__(self):
        """Initialise the visibility tracker."""
        # Per-player visibility records.
        self._player_records: dict[int, PlayerVisibilityRecord] = {}

        # Per-frame visibility snapshots.
        self._frame_records: list[FrameVisibility] = []

        # Per-frame visible zone tracking.
        self._zone_visibility_counts: dict[str, int] = defaultdict(int)

        # Total frames processed.
        self._total_frames: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        frame_index: int,
        visible_player_ids: list[int],
        visible_pitch_zones: list[str],
    ) -> None:
        """Record visibility data for a single frame.

        Args:
            frame_index: Zero-based frame index.
            visible_player_ids: List of player IDs visible in this frame.
            visible_pitch_zones: List of pitch zone names visible in this
                frame (from ``PITCH_ZONES``).
        """
        self._total_frames = max(self._total_frames, frame_index + 1)

        # Store frame record.
        coverage = len(visible_pitch_zones) / max(len(PITCH_ZONES), 1)
        frame_record = FrameVisibility(
            frame_index=frame_index,
            visible_player_ids=list(visible_player_ids),
            visible_pitch_zones=list(visible_pitch_zones),
            field_coverage_estimate=coverage,
        )
        self._frame_records.append(frame_record)

        # Update per-zone counts.
        for zone in visible_pitch_zones:
            self._zone_visibility_counts[zone] += 1

        # Update per-player records.
        for pid in visible_player_ids:
            if pid not in self._player_records:
                self._player_records[pid] = PlayerVisibilityRecord(
                    player_id=pid,
                    total_frame_count=self._total_frames,
                    first_seen_frame=frame_index,
                )

            record = self._player_records[pid]
            record.visible_frame_count += 1
            record.total_frame_count = self._total_frames
            record.last_seen_frame = frame_index
            record.visible_frame_indices.append(frame_index)

        # Update total_frame_count for players NOT seen this frame.
        for pid, record in self._player_records.items():
            record.total_frame_count = self._total_frames

    def get_screen_time_ratio(self, player_id: int) -> float:
        """Return the fraction of total frames where the player was visible.

        Args:
            player_id: Unique player identifier.

        Returns:
            Float in ``[0, 1]``.  Returns ``0.0`` if the player has never
            been observed.
        """
        record = self._player_records.get(player_id)
        if record is None:
            return 0.0
        return record.screen_time_ratio

    def get_adjusted_screen_time(
        self,
        player_id: int,
        formation: Optional[str] = None,
        position: Optional[str] = None,
    ) -> float:
        """Return screen time adjusted for expected off-screen time.

        Players in certain positions (e.g., fullbacks) are expected to be
        off-screen more often than central players.  This method computes
        an adjusted ratio that accounts for positional expectations.

        The adjustment formula:
            adjusted = raw_screen_time / expected_screen_time

        Capped at 1.0 (meaning the player was visible at least as much as
        expected).

        Args:
            player_id: Unique player identifier.
            formation: Formation string (e.g., ``"4-3-3"``).  Currently
                unused but reserved for formation-aware adjustments.
            position: Player position code (e.g., ``"CM"``, ``"LB"``).

        Returns:
            Adjusted screen time ratio in ``[0, 1]``.
        """
        raw = self.get_screen_time_ratio(player_id)

        if position is None:
            return raw

        expected = EXPECTED_SCREEN_TIME_BY_POSITION.get(
            position.upper(), 0.45
        )

        if expected <= 0:
            return raw

        adjusted = raw / expected
        return float(np.clip(adjusted, 0.0, 1.0))

    def get_data_density(self, player_id: int) -> float:
        """Return a confidence metric based on observation density.

        Combines screen time ratio with the consistency of observations
        (i.e., whether the player was seen in contiguous runs or scattered
        single frames).

        Args:
            player_id: Unique player identifier.

        Returns:
            Float in ``[0, 1]`` where higher values indicate more reliable
            data.
        """
        record = self._player_records.get(player_id)
        if record is None or record.visible_frame_count == 0:
            return 0.0

        screen_time = record.screen_time_ratio

        # Compute observation continuity: fraction of gaps that are small.
        indices = record.visible_frame_indices
        if len(indices) < 2:
            continuity = 0.5
        else:
            sorted_idx = sorted(indices)
            gaps = [
                sorted_idx[i + 1] - sorted_idx[i]
                for i in range(len(sorted_idx) - 1)
            ]
            small_gaps = sum(1 for g in gaps if g <= 3)
            continuity = small_gaps / len(gaps)

        # Weighted combination: screen time 60%, continuity 40%.
        density = 0.6 * screen_time + 0.4 * continuity
        return float(np.clip(density, 0.0, 1.0))

    def identify_high_value_frames(
        self,
        frame_data: Optional[list[FrameVisibility]] = None,
    ) -> list[int]:
        """Identify frames with maximum field coverage.

        High-value frames are those where the camera captures the most
        pitch zones -- typically during restarts, kickoffs, and wide shots.
        These frames are valuable for pitch calibration and formation
        analysis.

        Args:
            frame_data: Optional list of ``FrameVisibility`` records.  If
                ``None``, uses internally tracked data.

        Returns:
            Sorted list of frame indices with highest field coverage.
        """
        records = frame_data if frame_data is not None else self._frame_records

        if not records:
            return []

        # Score each frame by number of visible zones.
        scored: list[tuple[float, int]] = [
            (r.field_coverage_estimate, r.frame_index) for r in records
        ]

        # Sort by coverage descending.
        scored.sort(key=lambda x: x[0], reverse=True)

        # Return frames with coverage above the 80th percentile.
        if len(scored) == 0:
            return []

        threshold_idx = max(1, int(len(scored) * 0.20))
        threshold_coverage = scored[min(threshold_idx, len(scored) - 1)][0]

        high_value = [
            frame_idx
            for coverage, frame_idx in scored
            if coverage >= threshold_coverage
        ]

        # Sort by frame index for chronological order.
        high_value.sort()

        # Cap at a reasonable number for processing efficiency.
        max_frames = min(len(high_value), 50)
        if len(high_value) > max_frames:
            # Sample evenly across the high-value frames.
            step = len(high_value) / max_frames
            high_value = [
                high_value[int(i * step)] for i in range(max_frames)
            ]

        logger.info(
            "Identified %d high-value frames (coverage threshold: %.2f)",
            len(high_value),
            threshold_coverage,
        )
        return high_value

    def should_extrapolate(
        self,
        player_id: int,
        metric_name: str,
    ) -> bool:
        """Determine whether a metric should be extrapolated for a player.

        Extrapolation is appropriate when:
        1. The player has sufficient screen time (above the configured
           minimum threshold).
        2. The metric is of a type that can be meaningfully extrapolated
           (e.g., distance covered, not goals scored).

        Args:
            player_id: Unique player identifier.
            metric_name: Name of the metric to consider.

        Returns:
            ``True`` if the metric should be extrapolated.
        """
        # Never extrapolate discrete events.
        if metric_name in NON_EXTRAPOLATABLE_METRICS:
            return False

        # Only extrapolate continuous / rate-based metrics.
        if metric_name not in EXTRAPOLATABLE_METRICS:
            logger.debug(
                "Metric '%s' not in known extrapolatable set; defaulting to False",
                metric_name,
            )
            return False

        screen_time = self.get_screen_time_ratio(player_id)

        if screen_time < settings.min_screen_time_for_extrapolation:
            logger.debug(
                "Player %d screen time %.2f below threshold %.2f; "
                "will not extrapolate '%s'",
                player_id,
                screen_time,
                settings.min_screen_time_for_extrapolation,
                metric_name,
            )
            return False

        return True

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_player_record(
        self, player_id: int
    ) -> Optional[PlayerVisibilityRecord]:
        """Return the visibility record for a specific player."""
        return self._player_records.get(player_id)

    def get_all_player_records(self) -> dict[int, PlayerVisibilityRecord]:
        """Return all player visibility records."""
        return dict(self._player_records)

    def get_frame_record(self, frame_index: int) -> Optional[FrameVisibility]:
        """Return the visibility record for a specific frame."""
        for r in self._frame_records:
            if r.frame_index == frame_index:
                return r
        return None

    def get_zone_coverage_summary(self) -> dict[str, float]:
        """Return the fraction of frames each pitch zone was visible.

        Returns:
            Mapping of zone name to visibility fraction in ``[0, 1]``.
        """
        if self._total_frames == 0:
            return {zone: 0.0 for zone in PITCH_ZONES}

        return {
            zone: self._zone_visibility_counts.get(zone, 0) / self._total_frames
            for zone in PITCH_ZONES
        }

    def get_total_frames(self) -> int:
        """Return the total number of frames processed."""
        return self._total_frames

    def get_screen_time_warnings(self) -> list[dict]:
        """Return warnings for players with low screen time.

        Returns:
            List of dicts with ``player_id``, ``screen_time``, and
            ``message`` for each player below the warning threshold.
        """
        warnings: list[dict] = []
        for pid, record in self._player_records.items():
            st = record.screen_time_ratio
            if st < settings.screen_time_warning_threshold:
                warnings.append({
                    "player_id": pid,
                    "screen_time": round(st, 3),
                    "message": (
                        f"Player {pid} has only {st:.1%} screen time. "
                        f"Statistics may be less reliable."
                    ),
                })
        return warnings
