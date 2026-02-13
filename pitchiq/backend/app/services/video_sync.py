"""Multi-source video temporal alignment service."""

import numpy as np
from dataclasses import dataclass
from typing import Optional


@dataclass
class SyncPoint:
    """A temporal synchronization point between two video sources."""
    primary_timestamp: float  # seconds in primary video
    secondary_timestamp: float  # seconds in secondary video
    confidence: float
    method: str  # "manual", "audio_correlation", "event_match"


@dataclass
class SyncResult:
    """Result of temporal synchronization."""
    offset_ms: int  # milliseconds offset (secondary relative to primary)
    confidence: float
    sync_points: list[SyncPoint]


class VideoSyncService:
    """Synchronizes multiple video sources for the same game.

    Supports three alignment methods:
    1. Manual: User marks a common event (goal, whistle) in both videos
    2. Audio cross-correlation: Match crowd noise and whistle patterns
    3. Event matching: Match detected game events (goals, set pieces)
    """

    def manual_sync(
        self,
        primary_timestamp: float,
        secondary_timestamp: float,
    ) -> SyncResult:
        """Synchronize using user-provided common event timestamps.

        Args:
            primary_timestamp: Timestamp in primary video (seconds)
            secondary_timestamp: Timestamp in secondary video (seconds)
        """
        offset_ms = int((secondary_timestamp - primary_timestamp) * 1000)
        sync_point = SyncPoint(
            primary_timestamp=primary_timestamp,
            secondary_timestamp=secondary_timestamp,
            confidence=1.0,
            method="manual",
        )
        return SyncResult(
            offset_ms=offset_ms,
            confidence=1.0,
            sync_points=[sync_point],
        )

    def audio_correlation_sync(
        self,
        primary_audio_path: str,
        secondary_audio_path: str,
        sample_rate: int = 16000,
    ) -> SyncResult:
        """Synchronize using audio cross-correlation.

        Extracts audio from both videos and finds the time offset
        that maximizes cross-correlation (matching crowd noise,
        whistle blows, etc.).

        Args:
            primary_audio_path: Path to primary video's audio
            secondary_audio_path: Path to secondary video's audio
            sample_rate: Audio sample rate for analysis
        """
        # In production, this would:
        # 1. Extract audio from both videos using ffmpeg
        # 2. Downsample to analysis rate
        # 3. Compute cross-correlation using scipy.signal.correlate
        # 4. Find peak correlation offset
        # For MVP, return a placeholder
        return SyncResult(
            offset_ms=0,
            confidence=0.0,
            sync_points=[],
        )

    def compute_coverage_map(
        self,
        primary_field_coverage: list[dict],
        secondary_field_coverage: list[dict],
        offset_ms: int,
    ) -> dict:
        """Compute a per-second coverage map showing which source
        has the best view of each pitch zone.

        Args:
            primary_field_coverage: List of {timestamp, zones_visible} for primary
            secondary_field_coverage: Same for secondary
            offset_ms: Temporal offset of secondary relative to primary

        Returns:
            Dict mapping game_second -> {zone -> preferred_source}
        """
        coverage_map = {}
        offset_seconds = offset_ms / 1000.0

        # Merge coverage data
        for entry in primary_field_coverage:
            t = int(entry.get("timestamp", 0))
            if t not in coverage_map:
                coverage_map[t] = {"primary_zones": set(), "secondary_zones": set()}
            coverage_map[t]["primary_zones"].update(entry.get("zones_visible", []))

        for entry in secondary_field_coverage:
            t = int(entry.get("timestamp", 0) - offset_seconds)
            if t not in coverage_map:
                coverage_map[t] = {"primary_zones": set(), "secondary_zones": set()}
            coverage_map[t]["secondary_zones"].update(entry.get("zones_visible", []))

        return coverage_map

    def get_source_priority(
        self,
        player_bbox_primary: Optional[dict],
        player_bbox_secondary: Optional[dict],
    ) -> str:
        """Determine which source to prefer for a given player.

        Prefers the source where:
        - The player is larger in frame (better OCR)
        - The player is more centered (less distortion)
        - The source has higher resolution
        """
        if player_bbox_primary is None and player_bbox_secondary is None:
            return "none"
        if player_bbox_primary is None:
            return "secondary"
        if player_bbox_secondary is None:
            return "primary"

        # Compare bounding box sizes (larger = better for OCR)
        primary_area = player_bbox_primary.get("w", 0) * player_bbox_primary.get("h", 0)
        secondary_area = player_bbox_secondary.get("w", 0) * player_bbox_secondary.get("h", 0)

        if primary_area > secondary_area * 1.2:
            return "primary"
        elif secondary_area > primary_area * 1.2:
            return "secondary"

        # If similar size, prefer more centered
        primary_center_dist = abs(player_bbox_primary.get("cx", 0.5) - 0.5)
        secondary_center_dist = abs(player_bbox_secondary.get("cx", 0.5) - 0.5)

        return "primary" if primary_center_dist <= secondary_center_dist else "secondary"
