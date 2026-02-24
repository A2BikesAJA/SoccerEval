from __future__ import annotations

"""Multi-object player tracking service using ByteTrack-style assignment.

Maintains persistent identities across frames using Kalman filter prediction,
IoU-based matching, and appearance feature similarity for re-linking lost
tracks.
"""

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.spatial.distance import cosine as cosine_distance

from app.config import settings

logger = logging.getLogger(__name__)


class TrackState(Enum):
    """Lifecycle state of a track."""

    ACTIVE = "active"
    LOST = "lost"
    REMOVED = "removed"


@dataclass
class TrackRecord:
    """Internal record for a single tracked object."""

    track_id: int
    state: TrackState = TrackState.ACTIVE

    # Position history: list of (frame_index, cx, cy, w, h) tuples.
    positions: list[tuple[int, float, float, float, float]] = field(
        default_factory=list
    )
    velocities: list[tuple[float, float]] = field(default_factory=list)

    # Appearance feature (e.g., jersey colour embedding).
    appearance_features: list[np.ndarray] = field(default_factory=list)

    # Identity information aggregated from OCR, ReID, etc.
    identity_info: dict = field(default_factory=dict)

    # Kalman filter state: [cx, cy, w, h, vx, vy, vw, vh]
    kf_state: Optional[np.ndarray] = None
    kf_covariance: Optional[np.ndarray] = None

    # Timestamps for managing lost tracks.
    last_seen_time: float = 0.0
    first_seen_time: float = 0.0
    frames_since_update: int = 0
    total_visible_frames: int = 0

    # Original detection class and team assignment.
    class_label: str = "player"
    team: Optional[str] = None

    @property
    def last_position(self) -> Optional[tuple[float, float, float, float]]:
        """Return the most recent (cx, cy, w, h) or None."""
        if self.positions:
            return self.positions[-1][1:]  # type: ignore[return-value]
        return None

    @property
    def last_center(self) -> Optional[tuple[float, float]]:
        """Return the most recent centre (cx, cy)."""
        if self.positions:
            return (self.positions[-1][1], self.positions[-1][2])
        return None


class PlayerTracker:
    """ByteTrack-style multi-object tracker for soccer players.

    Features:
    - Kalman filter prediction for smooth state estimation.
    - Two-stage association: high-confidence first, then low-confidence.
    - Appearance similarity for re-linking lost tracks.
    - Configurable lost-track timeout (default 3 seconds).
    """

    # Kalman filter dimensionality: state = [cx, cy, w, h, vx, vy, vw, vh]
    STATE_DIM = 8
    MEAS_DIM = 4  # [cx, cy, w, h]

    # Association thresholds.
    IOU_THRESHOLD_HIGH = 0.3
    IOU_THRESHOLD_LOW = 0.1
    APPEARANCE_THRESHOLD = 0.60
    CONFIDENCE_SPLIT = 0.5  # Split detections into high/low confidence.

    # Track management.
    MAX_LOST_SECONDS = settings.track_lost_threshold_seconds
    MIN_HITS_TO_CONFIRM = 3

    def __init__(self, fps: float = 30.0):
        """Initialise the tracker.

        Args:
            fps: Frame rate of the video for time-based calculations.
        """
        self.fps = fps
        self._tracks: dict[int, TrackRecord] = {}
        self._next_id: int = 1
        self._frame_index: int = 0
        self._initialized: bool = False

        # Kalman filter matrices (constant velocity model).
        self._transition_matrix = self._build_transition_matrix()
        self._measurement_matrix = np.eye(self.MEAS_DIM, self.STATE_DIM, dtype=np.float64)
        self._process_noise = self._build_process_noise()
        self._measurement_noise = np.diag(
            [4.0, 4.0, 4.0, 4.0]
        ).astype(np.float64)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def initialize(
        self,
        first_frame_detections: list[dict],
    ) -> dict[int, dict]:
        """Create initial tracks from the first frame's detections.

        Args:
            first_frame_detections: List of detection dicts, each containing
                at minimum ``bbox`` (x1, y1, x2, y2), ``confidence``,
                ``class_label``.  Optionally ``appearance_feature``,
                ``team``.

        Returns:
            Mapping of ``track_id`` -> detection dict for all created tracks.
        """
        self._frame_index = 0
        self._tracks.clear()
        self._next_id = 1
        now = time.monotonic()

        assignments: dict[int, dict] = {}
        for det in first_frame_detections:
            bbox = det["bbox"]
            cx, cy, w, h = self._bbox_to_cxcywh(bbox)
            tid = self._create_track(cx, cy, w, h, now, det)
            assignments[tid] = det

        self._initialized = True
        logger.info(
            "Tracker initialised with %d tracks from first frame",
            len(assignments),
        )
        return assignments

    def update(
        self,
        detections: list[dict],
    ) -> dict[int, dict]:
        """Update tracks with a new frame's detections.

        Implements ByteTrack two-stage association:
        1. Match high-confidence detections to active tracks using IoU.
        2. Match remaining low-confidence detections to unmatched tracks.
        3. Attempt to re-link lost tracks using appearance similarity.
        4. Create new tracks for unmatched detections.

        Args:
            detections: List of detection dicts (same format as
                ``initialize``).

        Returns:
            Mapping of ``track_id`` -> detection dict for all matched and
            newly created tracks.
        """
        if not self._initialized:
            return self.initialize(detections)

        self._frame_index += 1
        now = time.monotonic()

        # Predict all active and lost tracks forward.
        for track in self._tracks.values():
            if track.state in (TrackState.ACTIVE, TrackState.LOST):
                self._kalman_predict(track)

        # Split detections by confidence.
        high_dets = [
            d for d in detections if d.get("confidence", 0) >= self.CONFIDENCE_SPLIT
        ]
        low_dets = [
            d for d in detections if d.get("confidence", 0) < self.CONFIDENCE_SPLIT
        ]

        active_tracks = [
            t for t in self._tracks.values() if t.state == TrackState.ACTIVE
        ]
        lost_tracks = [
            t for t in self._tracks.values() if t.state == TrackState.LOST
        ]

        assignments: dict[int, dict] = {}

        # Stage 1: Match high-confidence detections to active tracks.
        matched_track_ids_1, matched_det_indices_1, unmatched_tracks_1, unmatched_dets_1 = (
            self._associate(active_tracks, high_dets, self.IOU_THRESHOLD_HIGH)
        )

        for tid, det_idx in zip(matched_track_ids_1, matched_det_indices_1):
            det = high_dets[det_idx]
            self._update_track(self._tracks[tid], det, now)
            assignments[tid] = det

        # Stage 2: Match low-confidence detections to remaining active tracks.
        remaining_active = [
            self._tracks[tid]
            for tid in unmatched_tracks_1
            if self._tracks[tid].state == TrackState.ACTIVE
        ]
        matched_track_ids_2, matched_det_indices_2, unmatched_tracks_2, unmatched_dets_2 = (
            self._associate(remaining_active, low_dets, self.IOU_THRESHOLD_LOW)
        )

        for tid, det_idx in zip(matched_track_ids_2, matched_det_indices_2):
            det = low_dets[det_idx]
            self._update_track(self._tracks[tid], det, now)
            assignments[tid] = det

        # Stage 3: Try to re-link lost tracks with unmatched high-conf dets.
        unmatched_high_dets = [high_dets[i] for i in unmatched_dets_1]
        relinked_track_ids, relinked_det_indices = self._relink_lost_tracks(
            lost_tracks, unmatched_high_dets, now
        )

        relinked_det_set: set[int] = set()
        for tid, det_idx in zip(relinked_track_ids, relinked_det_indices):
            det = unmatched_high_dets[det_idx]
            track = self._tracks[tid]
            track.state = TrackState.ACTIVE
            self._update_track(track, det, now)
            assignments[tid] = det
            relinked_det_set.add(det_idx)

        # Stage 4: Create new tracks for fully unmatched high-conf detections.
        for i, det in enumerate(unmatched_high_dets):
            if i not in relinked_det_set:
                tid = self._create_track(
                    *self._bbox_to_cxcywh(det["bbox"]), now, det
                )
                assignments[tid] = det

        # Mark unmatched active tracks as lost.
        all_matched_track_ids = set(assignments.keys())
        for tid in list(unmatched_tracks_1) + [
            t.track_id for t in remaining_active if t.track_id not in all_matched_track_ids
        ]:
            track = self._tracks.get(tid)
            if track and track.state == TrackState.ACTIVE:
                track.state = TrackState.LOST
                track.frames_since_update += 1

        # Remove tracks that have been lost too long.
        for track in list(self._tracks.values()):
            if track.state == TrackState.LOST:
                elapsed = now - track.last_seen_time
                if elapsed > self.MAX_LOST_SECONDS:
                    track.state = TrackState.REMOVED
                    logger.debug("Track %d removed after %.1fs lost", track.track_id, elapsed)

        return assignments

    def get_track(self, track_id: int) -> Optional[TrackRecord]:
        """Return the full track record for a given track ID.

        Args:
            track_id: The unique track identifier.

        Returns:
            The ``TrackRecord`` or ``None`` if not found.
        """
        return self._tracks.get(track_id)

    def get_active_tracks(self) -> list[TrackRecord]:
        """Return all currently active tracks."""
        return [
            t for t in self._tracks.values() if t.state == TrackState.ACTIVE
        ]

    def get_all_tracks(self) -> dict[int, TrackRecord]:
        """Return the full track dictionary."""
        return dict(self._tracks)

    # ------------------------------------------------------------------
    # Association
    # ------------------------------------------------------------------

    def _associate(
        self,
        tracks: list[TrackRecord],
        detections: list[dict],
        iou_threshold: float,
    ) -> tuple[list[int], list[int], list[int], list[int]]:
        """Associate detections to tracks using IoU cost matrix.

        Returns:
            (matched_track_ids, matched_det_indices,
             unmatched_track_ids, unmatched_det_indices)
        """
        if not tracks or not detections:
            track_ids = [t.track_id for t in tracks]
            det_indices = list(range(len(detections)))
            return [], [], track_ids, det_indices

        # Build IoU cost matrix.
        cost_matrix = np.zeros(
            (len(tracks), len(detections)), dtype=np.float64
        )

        for i, track in enumerate(tracks):
            pred_bbox = self._predicted_bbox(track)
            if pred_bbox is None:
                cost_matrix[i, :] = 1.0
                continue
            for j, det in enumerate(detections):
                iou = self._compute_iou(pred_bbox, det["bbox"])
                cost_matrix[i, j] = 1.0 - iou

        # Hungarian assignment.
        row_indices, col_indices = linear_sum_assignment(cost_matrix)

        matched_tids: list[int] = []
        matched_dids: list[int] = []
        unmatched_tids: list[int] = list(range(len(tracks)))
        unmatched_dids: list[int] = list(range(len(detections)))

        for r, c in zip(row_indices, col_indices):
            if cost_matrix[r, c] <= (1.0 - iou_threshold):
                matched_tids.append(tracks[r].track_id)
                matched_dids.append(c)
                if r in unmatched_tids:
                    unmatched_tids.remove(r)
                if c in unmatched_dids:
                    unmatched_dids.remove(c)

        unmatched_track_ids = [tracks[i].track_id for i in unmatched_tids]
        return matched_tids, matched_dids, unmatched_track_ids, unmatched_dids

    def _relink_lost_tracks(
        self,
        lost_tracks: list[TrackRecord],
        detections: list[dict],
        now: float,
    ) -> tuple[list[int], list[int]]:
        """Try to re-link lost tracks using appearance + position similarity.

        Args:
            lost_tracks: Tracks currently in LOST state.
            detections: Unmatched high-confidence detections.
            now: Current monotonic timestamp.

        Returns:
            (relinked_track_ids, matched_detection_indices)
        """
        if not lost_tracks or not detections:
            return [], []

        relinked_tids: list[int] = []
        relinked_dids: list[int] = []
        used_dets: set[int] = set()

        for track in lost_tracks:
            elapsed = now - track.last_seen_time
            if elapsed > self.MAX_LOST_SECONDS:
                continue

            best_score = -1.0
            best_det_idx = -1

            pred_bbox = self._predicted_bbox(track)
            track_feat = (
                track.appearance_features[-1]
                if track.appearance_features
                else None
            )

            for j, det in enumerate(detections):
                if j in used_dets:
                    continue

                score = 0.0
                n_components = 0

                # Position similarity via IoU with predicted position.
                if pred_bbox is not None:
                    iou = self._compute_iou(pred_bbox, det["bbox"])
                    score += iou * 0.4
                    n_components += 1

                # Appearance similarity.
                det_feat = det.get("appearance_feature")
                if track_feat is not None and det_feat is not None:
                    sim = 1.0 - cosine_distance(track_feat, det_feat)
                    if sim >= self.APPEARANCE_THRESHOLD:
                        score += sim * 0.6
                        n_components += 1

                if n_components > 0 and score > best_score:
                    best_score = score
                    best_det_idx = j

            # Accept re-link if score is reasonable.
            if best_det_idx >= 0 and best_score > 0.25:
                relinked_tids.append(track.track_id)
                relinked_dids.append(best_det_idx)
                used_dets.add(best_det_idx)

        return relinked_tids, relinked_dids

    # ------------------------------------------------------------------
    # Track management
    # ------------------------------------------------------------------

    def _create_track(
        self,
        cx: float,
        cy: float,
        w: float,
        h: float,
        now: float,
        det: dict,
    ) -> int:
        """Create a new track and return its ID."""
        tid = self._next_id
        self._next_id += 1

        kf_state = np.array(
            [cx, cy, w, h, 0.0, 0.0, 0.0, 0.0], dtype=np.float64
        )
        kf_cov = np.eye(self.STATE_DIM, dtype=np.float64) * 100.0

        track = TrackRecord(
            track_id=tid,
            state=TrackState.ACTIVE,
            kf_state=kf_state,
            kf_covariance=kf_cov,
            last_seen_time=now,
            first_seen_time=now,
            class_label=det.get("class_label", "player"),
            team=det.get("team"),
        )
        track.positions.append(
            (self._frame_index, cx, cy, w, h)
        )
        track.total_visible_frames = 1

        feat = det.get("appearance_feature")
        if feat is not None:
            track.appearance_features.append(np.array(feat))

        self._tracks[tid] = track
        return tid

    def _update_track(
        self,
        track: TrackRecord,
        det: dict,
        now: float,
    ) -> None:
        """Update an existing track with a new detection."""
        bbox = det["bbox"]
        cx, cy, w, h = self._bbox_to_cxcywh(bbox)

        measurement = np.array([cx, cy, w, h], dtype=np.float64)
        self._kalman_update(track, measurement)

        # Compute velocity from last position.
        if track.positions:
            prev = track.positions[-1]
            dt = max(1.0 / self.fps, 1e-6)
            vx = (cx - prev[1]) / dt
            vy = (cy - prev[2]) / dt
            track.velocities.append((vx, vy))

        track.positions.append(
            (self._frame_index, cx, cy, w, h)
        )
        track.last_seen_time = now
        track.frames_since_update = 0
        track.total_visible_frames += 1
        track.state = TrackState.ACTIVE

        # Update appearance features (keep last 10).
        feat = det.get("appearance_feature")
        if feat is not None:
            track.appearance_features.append(np.array(feat))
            if len(track.appearance_features) > 10:
                track.appearance_features = track.appearance_features[-10:]

        # Update team assignment if provided.
        if det.get("team"):
            track.team = det["team"]

    # ------------------------------------------------------------------
    # Kalman filter
    # ------------------------------------------------------------------

    def _build_transition_matrix(self) -> np.ndarray:
        """Build the constant-velocity transition matrix F."""
        F = np.eye(self.STATE_DIM, dtype=np.float64)
        dt = 1.0  # Normalised time step
        for i in range(self.MEAS_DIM):
            F[i, self.MEAS_DIM + i] = dt
        return F

    def _build_process_noise(self) -> np.ndarray:
        """Build the process noise covariance Q."""
        Q = np.eye(self.STATE_DIM, dtype=np.float64)
        Q[:4, :4] *= 1.0
        Q[4:, 4:] *= 0.01
        return Q

    def _kalman_predict(self, track: TrackRecord) -> None:
        """Predict the track state one step forward."""
        if track.kf_state is None:
            return
        F = self._transition_matrix
        Q = self._process_noise
        track.kf_state = F @ track.kf_state
        track.kf_covariance = F @ track.kf_covariance @ F.T + Q
        track.frames_since_update += 1

    def _kalman_update(
        self, track: TrackRecord, measurement: np.ndarray
    ) -> None:
        """Correct the track state with a new measurement."""
        if track.kf_state is None:
            track.kf_state = np.array(
                [*measurement, 0.0, 0.0, 0.0, 0.0], dtype=np.float64
            )
            track.kf_covariance = np.eye(self.STATE_DIM, dtype=np.float64) * 100.0
            return

        H = self._measurement_matrix
        R = self._measurement_noise
        P = track.kf_covariance
        x = track.kf_state

        # Innovation.
        y = measurement - H @ x
        S = H @ P @ H.T + R
        try:
            K = P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            K = P @ H.T @ np.linalg.pinv(S)

        track.kf_state = x + K @ y
        I = np.eye(self.STATE_DIM, dtype=np.float64)
        track.kf_covariance = (I - K @ H) @ P

    def _predicted_bbox(
        self, track: TrackRecord
    ) -> Optional[tuple[float, float, float, float]]:
        """Return predicted bbox (x1, y1, x2, y2) from Kalman state."""
        if track.kf_state is None:
            return None
        cx, cy, w, h = track.kf_state[:4]
        return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)

    # ------------------------------------------------------------------
    # Geometry helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _bbox_to_cxcywh(
        bbox: tuple[float, float, float, float],
    ) -> tuple[float, float, float, float]:
        """Convert (x1, y1, x2, y2) to (cx, cy, w, h)."""
        x1, y1, x2, y2 = bbox
        return (
            (x1 + x2) / 2.0,
            (y1 + y2) / 2.0,
            x2 - x1,
            y2 - y1,
        )

    @staticmethod
    def _compute_iou(
        bbox_a: tuple[float, float, float, float],
        bbox_b: tuple[float, float, float, float],
    ) -> float:
        """Compute Intersection-over-Union between two bounding boxes."""
        x1 = max(bbox_a[0], bbox_b[0])
        y1 = max(bbox_a[1], bbox_b[1])
        x2 = min(bbox_a[2], bbox_b[2])
        y2 = min(bbox_a[3], bbox_b[3])

        inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
        area_a = (bbox_a[2] - bbox_a[0]) * (bbox_a[3] - bbox_a[1])
        area_b = (bbox_b[2] - bbox_b[0]) * (bbox_b[3] - bbox_b[1])
        union = area_a + area_b - inter

        if union <= 0:
            return 0.0
        return inter / union
