"""Ball tracking and possession attribution service.

Provides smooth ball trajectory estimation across frames, possession
attribution to the nearest player, possession change detection, and
out-of-play detection.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PossessionEvent:
    """Records a possession transition between players."""

    frame_index: int
    from_player_id: Optional[int]
    to_player_id: Optional[int]
    ball_position: tuple[float, float]
    event_type: str  # "gain", "loss", "transition", "contested"

    def to_dict(self) -> dict:
        return {
            "frame_index": self.frame_index,
            "from_player_id": self.from_player_id,
            "to_player_id": self.to_player_id,
            "ball_position": self.ball_position,
            "event_type": self.event_type,
        }


@dataclass
class BallState:
    """Ball state at a single frame."""

    frame_index: int
    position: Optional[tuple[float, float]]  # (x, y) in pixels
    confidence: float = 0.0
    is_interpolated: bool = False
    possessing_player_id: Optional[int] = None
    is_in_play: bool = True


class BallTracker:
    """Tracks the ball across frames and attributes possession to players.

    Features:
    - Kalman-smoothed ball trajectory filling short detection gaps.
    - Dynamic possession radius scaled by player bounding-box size.
    - Possession change detection with configurable hold time.
    - Out-of-play detection using field boundary coordinates.
    """

    # Maximum consecutive frames of missing ball before breaking trajectory.
    MAX_INTERPOLATION_GAP = 10

    # Possession radius as a fraction of average player height in frame.
    POSSESSION_RADIUS_FACTOR = 1.5

    # Minimum absolute possession radius in pixels.
    MIN_POSSESSION_RADIUS = 30.0

    # Number of frames a player must be nearest to "confirm" possession.
    POSSESSION_HOLD_FRAMES = 3

    # Kalman filter parameters for ball smoothing.
    KF_PROCESS_NOISE = 4.0
    KF_MEASUREMENT_NOISE = 16.0

    def __init__(self, fps: float = 30.0):
        """Initialise the ball tracker.

        Args:
            fps: Video frame rate for time-based calculations.
        """
        self.fps = fps
        self._trajectory: list[BallState] = []
        self._possession_history: list[Optional[int]] = []
        self._possession_events: list[PossessionEvent] = []
        self._current_possessor: Optional[int] = None
        self._possession_hold_counter: int = 0
        self._frame_index: int = 0

        # Kalman state for ball: [x, y, vx, vy]
        self._kf_state: Optional[np.ndarray] = None
        self._kf_cov: Optional[np.ndarray] = None
        self._kf_initialized: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def track_ball(
        self,
        detections_per_frame: list[Optional[tuple[float, float]]],
    ) -> list[BallState]:
        """Smooth ball trajectory across multiple frames.

        Fills short gaps in detection with Kalman-predicted positions and
        produces a continuous trajectory.

        Args:
            detections_per_frame: List where each element is either a
                ``(x, y)`` ball detection or ``None`` for that frame.

        Returns:
            List of ``BallState`` objects, one per input frame.
        """
        self._reset_kalman()
        trajectory: list[BallState] = []
        gap_count = 0

        for i, detection in enumerate(detections_per_frame):
            if detection is not None:
                x, y = detection
                if not self._kf_initialized:
                    self._init_kalman(x, y)
                else:
                    self._kalman_predict()
                    self._kalman_update(x, y)

                state = BallState(
                    frame_index=i,
                    position=(
                        float(self._kf_state[0]),
                        float(self._kf_state[1]),
                    ),
                    confidence=1.0,
                    is_interpolated=False,
                )
                gap_count = 0
            else:
                # No detection -- predict if within gap tolerance.
                if self._kf_initialized and gap_count < self.MAX_INTERPOLATION_GAP:
                    self._kalman_predict()
                    state = BallState(
                        frame_index=i,
                        position=(
                            float(self._kf_state[0]),
                            float(self._kf_state[1]),
                        ),
                        confidence=max(0.1, 1.0 - gap_count * 0.1),
                        is_interpolated=True,
                    )
                else:
                    state = BallState(
                        frame_index=i,
                        position=None,
                        confidence=0.0,
                        is_interpolated=False,
                    )
                gap_count += 1

            trajectory.append(state)

        self._trajectory = trajectory
        return trajectory

    def attribute_possession(
        self,
        ball_position: tuple[float, float],
        player_positions: dict[int, tuple[float, float, float, float]],
        frame_index: int = 0,
    ) -> Optional[int]:
        """Determine which player currently possesses the ball.

        Uses a dynamic possession radius scaled by the average player
        bounding-box height in frame.  The nearest player within the radius
        is assigned possession, subject to a hold-time filter to prevent
        rapid flickering.

        Args:
            ball_position: Ball centre ``(x, y)`` in pixels.
            player_positions: Mapping of ``player_id`` to bounding box
                ``(x1, y1, x2, y2)`` for all visible players.
            frame_index: Current frame index (for event logging).

        Returns:
            ``player_id`` of the player in possession, or ``None`` if no
            player is close enough.
        """
        if not player_positions:
            return None

        # Compute dynamic possession radius from average player height.
        avg_height = np.mean([
            bbox[3] - bbox[1] for bbox in player_positions.values()
        ])
        possession_radius = max(
            avg_height * self.POSSESSION_RADIUS_FACTOR,
            self.MIN_POSSESSION_RADIUS,
        )

        bx, by = ball_position
        nearest_id: Optional[int] = None
        nearest_dist: float = float("inf")

        for pid, bbox in player_positions.items():
            # Player foot position (bottom-centre of bbox).
            px = (bbox[0] + bbox[2]) / 2.0
            py = bbox[3]  # feet
            dist = np.sqrt((bx - px) ** 2 + (by - py) ** 2)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_id = pid

        if nearest_dist > possession_radius:
            # Ball is not close enough to any player -- contested / loose.
            candidate = None
        else:
            candidate = nearest_id

        # Apply hold-time filter.
        assigned = self._apply_hold_filter(candidate, frame_index)
        self._possession_history.append(assigned)
        return assigned

    def detect_possession_change(
        self,
        current_possessor: Optional[int],
        previous_possessor: Optional[int],
        frame_index: int = 0,
        ball_position: tuple[float, float] = (0.0, 0.0),
    ) -> Optional[PossessionEvent]:
        """Detect a transition in ball possession.

        Args:
            current_possessor: Player ID currently possessing the ball.
            previous_possessor: Player ID who previously had possession.
            frame_index: Current frame index.
            ball_position: Ball centre ``(x, y)`` at transition.

        Returns:
            A ``PossessionEvent`` if a change occurred, else ``None``.
        """
        if current_possessor == previous_possessor:
            return None

        if previous_possessor is None and current_possessor is not None:
            event_type = "gain"
        elif previous_possessor is not None and current_possessor is None:
            event_type = "loss"
        else:
            event_type = "transition"

        event = PossessionEvent(
            frame_index=frame_index,
            from_player_id=previous_possessor,
            to_player_id=current_possessor,
            ball_position=ball_position,
            event_type=event_type,
        )
        self._possession_events.append(event)
        logger.debug(
            "Possession %s: player %s -> player %s at frame %d",
            event_type,
            previous_possessor,
            current_possessor,
            frame_index,
        )
        return event

    def detect_out_of_play(
        self,
        ball_position: tuple[float, float],
        field_bounds: tuple[float, float, float, float],
    ) -> bool:
        """Determine whether the ball is outside the field of play.

        Args:
            ball_position: Ball centre ``(x, y)`` in pixels (or pitch
                coordinates if homography has been applied).
            field_bounds: ``(x_min, y_min, x_max, y_max)`` defining the
                rectangular field boundary.

        Returns:
            ``True`` if the ball is outside the field bounds.
        """
        bx, by = ball_position
        x_min, y_min, x_max, y_max = field_bounds

        # Small margin (2% of field size) to account for detection noise.
        margin_x = (x_max - x_min) * 0.02
        margin_y = (y_max - y_min) * 0.02

        out = (
            bx < x_min - margin_x
            or bx > x_max + margin_x
            or by < y_min - margin_y
            or by > y_max + margin_y
        )
        return out

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    def get_trajectory(self) -> list[BallState]:
        """Return the full smoothed ball trajectory."""
        return list(self._trajectory)

    def get_possession_events(self) -> list[PossessionEvent]:
        """Return all recorded possession transition events."""
        return list(self._possession_events)

    def get_possession_summary(self) -> dict[int, float]:
        """Return possession time fraction per player ID.

        Returns:
            Mapping of ``player_id`` -> fraction of total tracked frames
            where that player had possession.
        """
        total = len(self._possession_history)
        if total == 0:
            return {}

        counts: dict[int, int] = {}
        for pid in self._possession_history:
            if pid is not None:
                counts[pid] = counts.get(pid, 0) + 1

        return {pid: count / total for pid, count in counts.items()}

    # ------------------------------------------------------------------
    # Possession hold filter
    # ------------------------------------------------------------------

    def _apply_hold_filter(
        self,
        candidate: Optional[int],
        frame_index: int,
    ) -> Optional[int]:
        """Apply a hold-time filter to prevent rapid possession flickering.

        A new possession is only confirmed after the candidate has been the
        nearest player for ``POSSESSION_HOLD_FRAMES`` consecutive frames.

        Args:
            candidate: The nearest player candidate (or None).
            frame_index: Current frame index.

        Returns:
            The confirmed possessor after filtering.
        """
        previous = self._current_possessor

        if candidate == self._current_possessor:
            self._possession_hold_counter = 0
            return self._current_possessor

        self._possession_hold_counter += 1

        if self._possession_hold_counter >= self.POSSESSION_HOLD_FRAMES:
            # Confirm the change.
            ball_pos = (0.0, 0.0)
            if self._trajectory and frame_index < len(self._trajectory):
                state = self._trajectory[frame_index]
                if state.position is not None:
                    ball_pos = state.position

            self.detect_possession_change(
                candidate, previous, frame_index, ball_pos
            )
            self._current_possessor = candidate
            self._possession_hold_counter = 0
            return candidate

        # Hold not yet expired -- keep previous possessor.
        return self._current_possessor

    # ------------------------------------------------------------------
    # Kalman filter for ball smoothing
    # ------------------------------------------------------------------

    def _reset_kalman(self) -> None:
        """Reset the Kalman filter state."""
        self._kf_state = None
        self._kf_cov = None
        self._kf_initialized = False

    def _init_kalman(self, x: float, y: float) -> None:
        """Initialise Kalman state at the first observed ball position."""
        self._kf_state = np.array([x, y, 0.0, 0.0], dtype=np.float64)
        self._kf_cov = np.eye(4, dtype=np.float64) * 100.0
        self._kf_initialized = True

    def _kalman_predict(self) -> None:
        """Predict the ball state one time step forward."""
        if self._kf_state is None:
            return

        # Constant velocity transition matrix.
        F = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1],
        ], dtype=np.float64)

        Q = np.eye(4, dtype=np.float64) * self.KF_PROCESS_NOISE

        self._kf_state = F @ self._kf_state
        self._kf_cov = F @ self._kf_cov @ F.T + Q

    def _kalman_update(self, x: float, y: float) -> None:
        """Correct the Kalman state with a new ball observation."""
        if self._kf_state is None:
            self._init_kalman(x, y)
            return

        H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
        ], dtype=np.float64)

        R = np.eye(2, dtype=np.float64) * self.KF_MEASUREMENT_NOISE

        z = np.array([x, y], dtype=np.float64)
        y_innov = z - H @ self._kf_state
        S = H @ self._kf_cov @ H.T + R

        try:
            K = self._kf_cov @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            K = self._kf_cov @ H.T @ np.linalg.pinv(S)

        self._kf_state = self._kf_state + K @ y_innov
        I = np.eye(4, dtype=np.float64)
        self._kf_cov = (I - K @ H) @ self._kf_cov
