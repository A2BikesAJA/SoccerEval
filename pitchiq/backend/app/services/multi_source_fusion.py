"""Multi-source video fusion service.

Merges tracking data from multiple camera sources to increase
player coverage and improve tracking accuracy.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class FusedPlayerTrack:
    """A player track merged from multiple video sources."""
    player_id: int
    source_tracks: dict[str, list] = field(default_factory=dict)
    # source_id -> list of (timestamp, x, y, bbox, confidence)
    merged_positions: list = field(default_factory=list)
    total_visible_frames: int = 0
    sources_visible: set = field(default_factory=set)


class MultiSourceFusion:
    """Merges player tracking across multiple video sources.

    Handles:
    - Matching players across camera angles using appearance embeddings
    - Combining tracking data to increase screen time coverage
    - Selecting best source for OCR per frame
    - Computing aggregate screen time (union across all sources)
    """

    def __init__(self, similarity_threshold: float = 0.75):
        self.similarity_threshold = similarity_threshold
        self.player_tracks: dict[int, FusedPlayerTrack] = {}

    def match_player_across_sources(
        self,
        primary_embedding: np.ndarray,
        secondary_embeddings: list[np.ndarray],
        secondary_ids: list[int],
    ) -> Optional[int]:
        """Match a player from the primary source to the secondary source
        using appearance embeddings.

        Args:
            primary_embedding: 512-dim embedding from primary source
            secondary_embeddings: List of embeddings from secondary source
            secondary_ids: Corresponding player IDs in secondary source

        Returns:
            Matched player ID from secondary, or None if no match
        """
        if len(secondary_embeddings) == 0:
            return None

        # Compute cosine similarities
        similarities = []
        for emb in secondary_embeddings:
            if primary_embedding is not None and emb is not None:
                sim = np.dot(primary_embedding, emb) / (
                    np.linalg.norm(primary_embedding) * np.linalg.norm(emb) + 1e-8
                )
                similarities.append(sim)
            else:
                similarities.append(0.0)

        best_idx = int(np.argmax(similarities))
        best_sim = similarities[best_idx]

        if best_sim >= self.similarity_threshold:
            return secondary_ids[best_idx]
        return None

    def merge_tracking_data(
        self,
        primary_tracks: dict[int, list],
        secondary_tracks: dict[int, list],
        player_mapping: dict[int, int],
        temporal_offset_ms: int = 0,
    ) -> dict[int, FusedPlayerTrack]:
        """Merge tracking data from two sources using player ID mapping.

        Args:
            primary_tracks: {player_id: [(timestamp, x, y, bbox, confidence), ...]}
            secondary_tracks: Same format for secondary source
            player_mapping: {primary_player_id: secondary_player_id}
            temporal_offset_ms: Time offset of secondary relative to primary

        Returns:
            Dict of fused player tracks
        """
        offset_seconds = temporal_offset_ms / 1000.0
        fused = {}

        # Add all primary tracks
        for pid, positions in primary_tracks.items():
            track = FusedPlayerTrack(player_id=pid)
            track.source_tracks["primary"] = positions
            track.sources_visible.add("primary")
            fused[pid] = track

        # Merge secondary tracks
        for primary_id, secondary_id in player_mapping.items():
            if secondary_id in secondary_tracks:
                secondary_positions = secondary_tracks[secondary_id]
                # Adjust timestamps for temporal offset
                adjusted = [
                    (ts - offset_seconds, x, y, bbox, conf)
                    for ts, x, y, bbox, conf in secondary_positions
                ]

                if primary_id in fused:
                    fused[primary_id].source_tracks["secondary"] = adjusted
                    fused[primary_id].sources_visible.add("secondary")

        # Add unmatched secondary tracks
        matched_secondary = set(player_mapping.values())
        for sid, positions in secondary_tracks.items():
            if sid not in matched_secondary:
                # This player was only visible in secondary
                track = FusedPlayerTrack(player_id=sid + 1000)
                adjusted = [
                    (ts - offset_seconds, x, y, bbox, conf)
                    for ts, x, y, bbox, conf in positions
                ]
                track.source_tracks["secondary"] = adjusted
                track.sources_visible.add("secondary")
                fused[sid + 1000] = track

        # Merge positions for each player
        for pid, track in fused.items():
            track.merged_positions = self._merge_positions(track.source_tracks)
            track.total_visible_frames = len(track.merged_positions)

        self.player_tracks = fused
        return fused

    def _merge_positions(self, source_tracks: dict[str, list]) -> list:
        """Merge positions from multiple sources, preferring the source
        with higher confidence at each timestamp."""
        all_positions = {}

        for source_id, positions in source_tracks.items():
            for entry in positions:
                ts = round(entry[0], 1)  # Round to 0.1s buckets
                if ts not in all_positions or entry[4] > all_positions[ts][4]:
                    all_positions[ts] = entry

        return sorted(all_positions.values(), key=lambda x: x[0])

    def compute_aggregate_screen_time(
        self,
        player_id: int,
        total_game_seconds: float,
    ) -> float:
        """Compute screen time as the union of visibility across all sources.

        A player is "visible" at time t if they appear in ANY source.
        This is always >= the screen time from any single source.
        """
        track = self.player_tracks.get(player_id)
        if not track:
            return 0.0

        # Collect all unique timestamps (rounded to 0.5s)
        visible_times = set()
        for source_positions in track.source_tracks.values():
            for entry in source_positions:
                visible_times.add(round(entry[0] * 2) / 2)

        return len(visible_times) * 0.5 / max(1.0, total_game_seconds)

    def get_best_source_for_ocr(
        self,
        player_id: int,
        timestamp: float,
    ) -> Optional[str]:
        """Determine which source has the best view for OCR at a given time.

        Prefers the source where the player's bounding box is largest
        (closer to camera = better jersey number visibility).
        """
        track = self.player_tracks.get(player_id)
        if not track:
            return None

        best_source = None
        best_bbox_area = 0

        for source_id, positions in track.source_tracks.items():
            for entry in positions:
                if abs(entry[0] - timestamp) < 0.5:
                    bbox = entry[3]
                    if bbox:
                        area = bbox.get("w", 0) * bbox.get("h", 0)
                        if area > best_bbox_area:
                            best_bbox_area = area
                            best_source = source_id

        return best_source
