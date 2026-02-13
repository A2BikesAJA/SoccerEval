"""Player detection service using YOLOv8.

Detects players, referees, balls, and goalposts in video frames, then
classifies detected players into teams based on jersey color clustering.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import cv2
import numpy as np
from sklearn.cluster import KMeans

from app.config import settings

logger = logging.getLogger(__name__)

# YOLO class IDs mapped to soccer-relevant categories.
# Standard COCO: 0=person, 32=sports ball.
# Custom fine-tuned model may add goalpost as a separate class.
COCO_PERSON_CLASS = 0
COCO_BALL_CLASS = 32

# Detection class labels used throughout the pipeline.
CLASS_PLAYER = "player"
CLASS_REFEREE = "referee"
CLASS_BALL = "ball"
CLASS_GOALPOST = "goalpost"


@dataclass
class Detection:
    """Single object detection result."""

    bbox: tuple[float, float, float, float]  # (x1, y1, x2, y2) in pixels
    confidence: float
    class_label: str  # player, referee, ball, goalpost
    team: Optional[str] = None  # "team_a", "team_b", "referee", or None
    track_id: Optional[int] = None
    jersey_color_rgb: Optional[tuple[int, int, int]] = None
    metadata: dict = field(default_factory=dict)

    @property
    def center(self) -> tuple[float, float]:
        """Return the center point of the bounding box."""
        x1, y1, x2, y2 = self.bbox
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)

    @property
    def width(self) -> float:
        return self.bbox[2] - self.bbox[0]

    @property
    def height(self) -> float:
        return self.bbox[3] - self.bbox[1]

    @property
    def area(self) -> float:
        return self.width * self.height


class PlayerDetector:
    """Detects and classifies soccer players in video frames using YOLOv8.

    The detector performs three main tasks:
    1. Object detection (players, ball, goalposts) via YOLO.
    2. Team classification via K-Means clustering on jersey colours.
    3. Dedicated ball detection with size/shape filtering.
    """

    # Minimum confidence thresholds per class.
    DEFAULT_PERSON_CONF = 0.35
    DEFAULT_BALL_CONF = 0.25

    # Upper-body crop ratios for jersey colour extraction.
    UPPER_BODY_TOP_RATIO = 0.15  # Skip head area
    UPPER_BODY_BOTTOM_RATIO = 0.50  # Stop at waist

    # Ball physical constraints (relative to frame height).
    BALL_MAX_HEIGHT_RATIO = 0.06
    BALL_MIN_HEIGHT_RATIO = 0.004

    def __init__(
        self,
        model_path: Optional[str] = None,
        person_conf: float = DEFAULT_PERSON_CONF,
        ball_conf: float = DEFAULT_BALL_CONF,
    ):
        """Initialise the player detector.

        Args:
            model_path: Path to the YOLOv8 weights file. Falls back to the
                value in ``settings.yolo_model_path``.
            person_conf: Minimum confidence for person detections.
            ball_conf: Minimum confidence for ball detections.
        """
        self.model_path = model_path or settings.yolo_model_path
        self.person_conf = person_conf
        self.ball_conf = ball_conf
        self._model = None
        self._team_kmeans: Optional[KMeans] = None

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _load_model(self):
        """Lazy-load the YOLO model on first use."""
        if self._model is not None:
            return
        try:
            from ultralytics import YOLO

            self._model = YOLO(self.model_path)
            logger.info("Loaded YOLO model from %s", self.model_path)
        except Exception as exc:
            logger.error("Failed to load YOLO model: %s", exc)
            raise RuntimeError(
                f"Could not load YOLO model from {self.model_path}"
            ) from exc

    # ------------------------------------------------------------------
    # Detection
    # ------------------------------------------------------------------

    def detect_players(self, frame_path: str) -> list[Detection]:
        """Run detection on a single frame and return all relevant objects.

        Args:
            frame_path: Absolute path to the frame image file.

        Returns:
            List of ``Detection`` objects for players, referees, balls, and
            goalposts found in the frame.
        """
        self._load_model()

        frame_path = str(frame_path)
        frame = cv2.imread(frame_path)
        if frame is None:
            logger.warning("Could not read frame at %s", frame_path)
            return []

        frame_h, frame_w = frame.shape[:2]

        results = self._model(frame, verbose=False)[0]
        detections: list[Detection] = []

        for box in results.boxes:
            cls_id = int(box.cls[0])
            conf = float(box.conf[0])
            x1, y1, x2, y2 = box.xyxy[0].tolist()

            if cls_id == COCO_PERSON_CLASS and conf >= self.person_conf:
                det = Detection(
                    bbox=(x1, y1, x2, y2),
                    confidence=conf,
                    class_label=CLASS_PLAYER,
                )
                # Extract dominant jersey colour for downstream clustering.
                color = self._extract_jersey_color(frame, det.bbox)
                det.jersey_color_rgb = color
                detections.append(det)

            elif cls_id == COCO_BALL_CLASS and conf >= self.ball_conf:
                box_h = y2 - y1
                h_ratio = box_h / frame_h
                if self.BALL_MIN_HEIGHT_RATIO <= h_ratio <= self.BALL_MAX_HEIGHT_RATIO:
                    detections.append(
                        Detection(
                            bbox=(x1, y1, x2, y2),
                            confidence=conf,
                            class_label=CLASS_BALL,
                        )
                    )

        # Check for goalpost detections if the model supports them.
        goalpost_dets = self._detect_goalposts(results, frame_h, frame_w)
        detections.extend(goalpost_dets)

        logger.debug(
            "Detected %d objects in %s (players=%d, balls=%d)",
            len(detections),
            frame_path,
            sum(1 for d in detections if d.class_label == CLASS_PLAYER),
            sum(1 for d in detections if d.class_label == CLASS_BALL),
        )
        return detections

    def detect_ball(self, frame_path: str) -> Optional[tuple[float, float]]:
        """Detect the ball in a frame and return its centre position.

        Args:
            frame_path: Absolute path to the frame image file.

        Returns:
            ``(cx, cy)`` pixel coordinates of the ball centre, or ``None`` if
            the ball was not detected.
        """
        detections = self.detect_players(frame_path)
        ball_dets = [d for d in detections if d.class_label == CLASS_BALL]
        if not ball_dets:
            return None

        # Take the highest-confidence ball detection.
        best = max(ball_dets, key=lambda d: d.confidence)
        return best.center

    # ------------------------------------------------------------------
    # Team classification
    # ------------------------------------------------------------------

    def classify_teams(
        self,
        detections: list[Detection],
        frame: np.ndarray,
        n_teams: int = 2,
    ) -> list[Detection]:
        """Classify player detections into Team A, Team B, and referees.

        Uses K-Means clustering on the dominant jersey colour extracted from
        the upper-body region of each detected player.

        Args:
            detections: Detections from ``detect_players``.
            frame: The BGR image as a numpy array.
            n_teams: Expected number of team clusters (default 2).

        Returns:
            The same list of ``Detection`` objects with the ``team`` field
            populated (``"team_a"``, ``"team_b"``, or ``"referee"``).
        """
        player_dets = [
            d for d in detections if d.class_label == CLASS_PLAYER
        ]

        if len(player_dets) < n_teams + 1:
            # Not enough players to cluster meaningfully.
            for d in player_dets:
                d.team = "team_a"
            return detections

        # Build colour feature matrix from jersey colours.
        colors: list[np.ndarray] = []
        valid_indices: list[int] = []
        for idx, det in enumerate(player_dets):
            color = det.jersey_color_rgb
            if color is None:
                color = self._extract_jersey_color(frame, det.bbox)
                det.jersey_color_rgb = color
            if color is not None:
                colors.append(np.array(color, dtype=np.float64))
                valid_indices.append(idx)

        if len(colors) < n_teams + 1:
            return detections

        color_matrix = np.array(colors)

        # Cluster into n_teams + 1 groups (teams + referees).
        n_clusters = min(n_teams + 1, len(colors))
        kmeans = KMeans(n_clusters=n_clusters, n_init=10, random_state=42)
        labels = kmeans.fit_predict(color_matrix)
        self._team_kmeans = kmeans

        # Identify the referee cluster: typically the smallest or the one
        # whose centre is darkest (black kit is common for referees).
        cluster_sizes = np.bincount(labels, minlength=n_clusters)
        cluster_brightness = [
            np.mean(kmeans.cluster_centers_[i]) for i in range(n_clusters)
        ]

        # Heuristic: referee cluster is the one that is either smallest or
        # darkest.  We score each cluster and pick the most likely referee
        # cluster.
        referee_scores = np.zeros(n_clusters)
        size_order = np.argsort(cluster_sizes)
        bright_order = np.argsort(cluster_brightness)

        for rank, cid in enumerate(size_order):
            referee_scores[cid] += rank  # smaller clusters score higher
        for rank, cid in enumerate(bright_order):
            referee_scores[cid] += rank  # darker clusters score higher

        referee_cluster = int(np.argmin(referee_scores))

        # Assign the two largest non-referee clusters as team_a and team_b.
        team_clusters = [
            c for c in range(n_clusters) if c != referee_cluster
        ]
        # Sort by cluster size descending so team_a is the larger group.
        team_clusters.sort(key=lambda c: cluster_sizes[c], reverse=True)

        label_to_team = {}
        if len(team_clusters) >= 1:
            label_to_team[team_clusters[0]] = "team_a"
        if len(team_clusters) >= 2:
            label_to_team[team_clusters[1]] = "team_b"
        label_to_team[referee_cluster] = "referee"

        for i, vi in enumerate(valid_indices):
            cluster_label = labels[i]
            team_name = label_to_team.get(cluster_label, "team_a")
            player_dets[vi].team = team_name

            # Update class_label for referees.
            if team_name == "referee":
                player_dets[vi].class_label = CLASS_REFEREE

        return detections

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _extract_jersey_color(
        self, frame: np.ndarray, bbox: tuple[float, float, float, float]
    ) -> Optional[tuple[int, int, int]]:
        """Extract the dominant jersey colour from the upper-body region.

        Args:
            frame: BGR image as numpy array.
            bbox: Bounding box ``(x1, y1, x2, y2)``.

        Returns:
            Dominant colour as ``(R, G, B)`` tuple, or ``None`` on failure.
        """
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h = y2 - y1
        w = x2 - x1

        if h <= 0 or w <= 0:
            return None

        # Crop upper-body (torso) region, skipping head and legs.
        torso_y1 = y1 + int(h * self.UPPER_BODY_TOP_RATIO)
        torso_y2 = y1 + int(h * self.UPPER_BODY_BOTTOM_RATIO)

        # Narrow horizontally to avoid arms/background.
        torso_x1 = x1 + int(w * 0.2)
        torso_x2 = x2 - int(w * 0.2)

        fh, fw = frame.shape[:2]
        torso_y1 = max(0, min(torso_y1, fh - 1))
        torso_y2 = max(0, min(torso_y2, fh - 1))
        torso_x1 = max(0, min(torso_x1, fw - 1))
        torso_x2 = max(0, min(torso_x2, fw - 1))

        if torso_y2 <= torso_y1 or torso_x2 <= torso_x1:
            return None

        crop = frame[torso_y1:torso_y2, torso_x1:torso_x2]
        if crop.size == 0:
            return None

        # Convert to RGB and compute the mean colour.
        crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)

        # Use K-Means with k=2 on the crop to separate jersey from
        # background/shorts, then take the larger cluster.
        pixels = crop_rgb.reshape(-1, 3).astype(np.float64)
        if len(pixels) < 10:
            mean_color = np.mean(pixels, axis=0)
            return tuple(int(c) for c in mean_color)  # type: ignore[return-value]

        km = KMeans(n_clusters=2, n_init=4, random_state=0)
        km.fit(pixels)
        counts = np.bincount(km.labels_)
        dominant_idx = int(np.argmax(counts))
        dominant_color = km.cluster_centers_[dominant_idx]

        return tuple(int(c) for c in dominant_color)  # type: ignore[return-value]

    def _detect_goalposts(
        self, results, frame_h: int, frame_w: int
    ) -> list[Detection]:
        """Extract goalpost detections from YOLO results.

        If the model does not have a dedicated goalpost class, this method
        returns an empty list.  In production, a fine-tuned model would
        include goalposts as a separate class.
        """
        detections: list[Detection] = []
        # Custom-trained models may expose goalposts at class index 80+.
        # Check if any class name contains "goalpost" or "goal".
        if not hasattr(results, "names"):
            return detections

        goalpost_cls_ids = [
            cid
            for cid, name in results.names.items()
            if "goal" in name.lower()
        ]

        if not goalpost_cls_ids:
            return detections

        for box in results.boxes:
            cls_id = int(box.cls[0])
            if cls_id in goalpost_cls_ids:
                conf = float(box.conf[0])
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        bbox=(x1, y1, x2, y2),
                        confidence=conf,
                        class_label=CLASS_GOALPOST,
                    )
                )

        return detections
