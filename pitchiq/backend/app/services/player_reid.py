"""Player re-identification service.

Extracts appearance embeddings from player crops and matches them against
a gallery of known identities.  Uses cosine similarity for matching.

In production this module would load a real OSNet or similar ReID model.
For MVP, it produces deterministic simulated embeddings derived from image
content that are consistent enough to demonstrate the matching pipeline.
"""

import logging
from typing import Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Embedding dimensionality (matches OSNet output).
EMBEDDING_DIM = 512


class PlayerReID:
    """Extracts and matches player appearance embeddings.

    Gallery management:
    - Each gallery entry maps a ``player_id`` to a running-average
      embedding built from all observations of that player.
    - Matching uses cosine similarity with a configurable threshold.
    """

    def __init__(
        self,
        similarity_threshold: float = settings.reid_similarity_threshold,
        embedding_dim: int = EMBEDDING_DIM,
    ):
        """Initialise the ReID service.

        Args:
            similarity_threshold: Minimum cosine similarity to accept a
                gallery match.
            embedding_dim: Dimensionality of the appearance embedding vector.
        """
        self.similarity_threshold = similarity_threshold
        self.embedding_dim = embedding_dim

        # Gallery: player_id -> {"embedding": np.ndarray, "count": int}
        self._gallery: dict[int, dict] = {}

        # Model placeholder (set to a real model in production).
        self._model = None
        self._model_loaded = False

    # ------------------------------------------------------------------
    # Model loading
    # ------------------------------------------------------------------

    def _ensure_model(self) -> None:
        """Attempt to load the ReID model.  Falls back to simulated mode."""
        if self._model_loaded:
            return
        try:
            # Production integration point: load torchreid / OSNet here.
            # from torchreid.utils import FeatureExtractor
            # self._model = FeatureExtractor(model_name='osnet_x1_0', ...)
            logger.info(
                "ReID model not available; using simulated embeddings "
                "(suitable for MVP testing)"
            )
        except Exception as exc:
            logger.warning("Failed to load ReID model: %s", exc)
        self._model_loaded = True

    # ------------------------------------------------------------------
    # Embedding extraction
    # ------------------------------------------------------------------

    def extract_embedding(
        self,
        frame: np.ndarray,
        bbox: tuple[float, float, float, float],
    ) -> np.ndarray:
        """Extract a 512-dimensional appearance embedding for a player crop.

        Args:
            frame: Full BGR frame as a numpy array.
            bbox: Player bounding box ``(x1, y1, x2, y2)`` in pixels.

        Returns:
            A 1-D numpy array of shape ``(embedding_dim,)`` with L2 norm
            equal to 1.
        """
        self._ensure_model()

        crop = self._crop_and_resize(frame, bbox)
        if crop is None:
            return self._random_embedding()

        if self._model is not None:
            return self._extract_with_model(crop)

        return self._extract_simulated(crop)

    def _extract_with_model(self, crop: np.ndarray) -> np.ndarray:
        """Extract embedding using the loaded ReID model.

        Args:
            crop: Resized BGR player crop.

        Returns:
            L2-normalised embedding vector.
        """
        # Placeholder for real model inference.
        # embedding = self._model([crop])[0]
        # return self._l2_normalize(embedding)
        return self._extract_simulated(crop)

    def _extract_simulated(self, crop: np.ndarray) -> np.ndarray:
        """Produce a deterministic simulated embedding from image content.

        The embedding is derived from downsampled colour statistics of the
        player crop so that visually similar players produce similar
        vectors.  This is *not* a production-quality embedding but is
        sufficient for pipeline integration testing.

        Args:
            crop: Resized BGR player crop (128x256).

        Returns:
            L2-normalised embedding vector of shape ``(embedding_dim,)``.
        """
        # Downsample to a small thumbnail for colour statistics.
        thumb = cv2.resize(crop, (16, 32), interpolation=cv2.INTER_AREA)
        hsv = cv2.cvtColor(thumb, cv2.COLOR_BGR2HSV).astype(np.float64)

        # Build a raw feature vector from spatial colour statistics.
        # Split into 4x4 grid, compute mean H, S, V per cell.
        grid_h, grid_w = 4, 4
        cell_h = hsv.shape[0] // grid_h
        cell_w = hsv.shape[1] // grid_w
        features = []

        for r in range(grid_h):
            for c in range(grid_w):
                cell = hsv[
                    r * cell_h : (r + 1) * cell_h,
                    c * cell_w : (c + 1) * cell_w,
                ]
                features.extend([
                    np.mean(cell[:, :, 0]),  # Hue
                    np.std(cell[:, :, 0]),
                    np.mean(cell[:, :, 1]),  # Saturation
                    np.mean(cell[:, :, 2]),  # Value
                ])

        raw = np.array(features, dtype=np.float64)

        # Project to embedding_dim using a deterministic pseudo-random
        # projection matrix (seeded for reproducibility).
        rng = np.random.RandomState(42)
        projection = rng.randn(len(raw), self.embedding_dim).astype(np.float64)
        embedding = raw @ projection

        return self._l2_normalize(embedding)

    # ------------------------------------------------------------------
    # Similarity computation
    # ------------------------------------------------------------------

    @staticmethod
    def compute_similarity(
        embedding1: np.ndarray,
        embedding2: np.ndarray,
    ) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First L2-normalised embedding.
            embedding2: Second L2-normalised embedding.

        Returns:
            Cosine similarity in ``[-1, 1]`` (higher is more similar).
        """
        dot = float(np.dot(embedding1, embedding2))
        norm1 = float(np.linalg.norm(embedding1))
        norm2 = float(np.linalg.norm(embedding2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    def match_to_gallery(
        self,
        embedding: np.ndarray,
        gallery: Optional[dict[int, dict]] = None,
    ) -> tuple[Optional[int], float]:
        """Find the best-matching gallery entry for an embedding.

        Args:
            embedding: Query embedding vector.
            gallery: Optional external gallery dict.  If ``None``, uses the
                internal gallery.

        Returns:
            ``(player_id, similarity_score)`` of the best match, or
            ``(None, 0.0)`` if no match exceeds the threshold.
        """
        target_gallery = gallery if gallery is not None else self._gallery

        if not target_gallery:
            return None, 0.0

        best_id: Optional[int] = None
        best_score: float = 0.0

        for pid, entry in target_gallery.items():
            gallery_emb = entry["embedding"]
            sim = self.compute_similarity(embedding, gallery_emb)
            if sim > best_score:
                best_score = sim
                best_id = pid

        if best_score >= self.similarity_threshold:
            return best_id, best_score

        return None, best_score

    # ------------------------------------------------------------------
    # Gallery management
    # ------------------------------------------------------------------

    def add_to_gallery(
        self,
        player_id: int,
        embedding: np.ndarray,
    ) -> None:
        """Add or update a player's gallery embedding using running average.

        Args:
            player_id: Unique player identifier.
            embedding: New L2-normalised embedding observation.
        """
        if player_id in self._gallery:
            entry = self._gallery[player_id]
            count = entry["count"]
            # Incremental mean update.
            updated = (entry["embedding"] * count + embedding) / (count + 1)
            entry["embedding"] = self._l2_normalize(updated)
            entry["count"] = count + 1
        else:
            self._gallery[player_id] = {
                "embedding": self._l2_normalize(embedding.copy()),
                "count": 1,
            }
        logger.debug(
            "Gallery updated for player %d (total observations: %d)",
            player_id,
            self._gallery[player_id]["count"],
        )

    def get_gallery_embedding(
        self, player_id: int
    ) -> Optional[np.ndarray]:
        """Return the current gallery embedding for a player.

        Args:
            player_id: Unique player identifier.

        Returns:
            The gallery embedding vector, or ``None`` if the player is not
            in the gallery.
        """
        entry = self._gallery.get(player_id)
        if entry is not None:
            return entry["embedding"].copy()
        return None

    def get_gallery_size(self) -> int:
        """Return the number of players in the gallery."""
        return len(self._gallery)

    def clear_gallery(self) -> None:
        """Remove all entries from the gallery."""
        self._gallery.clear()
        logger.info("ReID gallery cleared")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _crop_and_resize(
        self,
        frame: np.ndarray,
        bbox: tuple[float, float, float, float],
        target_size: tuple[int, int] = (128, 256),
    ) -> Optional[np.ndarray]:
        """Crop the player from the frame and resize for embedding.

        Args:
            frame: Full BGR frame.
            bbox: Bounding box ``(x1, y1, x2, y2)``.
            target_size: ``(width, height)`` to resize to.

        Returns:
            Resized BGR crop, or ``None`` on failure.
        """
        x1, y1, x2, y2 = [int(v) for v in bbox]
        fh, fw = frame.shape[:2]
        x1 = max(0, min(x1, fw - 1))
        x2 = max(0, min(x2, fw - 1))
        y1 = max(0, min(y1, fh - 1))
        y2 = max(0, min(y2, fh - 1))

        if x2 <= x1 or y2 <= y1:
            return None

        crop = frame[y1:y2, x1:x2]
        if crop.size == 0:
            return None

        resized = cv2.resize(
            crop, target_size, interpolation=cv2.INTER_LINEAR
        )
        return resized

    def _random_embedding(self) -> np.ndarray:
        """Generate a random L2-normalised embedding (fallback)."""
        vec = np.random.randn(self.embedding_dim).astype(np.float64)
        return self._l2_normalize(vec)

    @staticmethod
    def _l2_normalize(vec: np.ndarray) -> np.ndarray:
        """L2-normalise a vector. Returns zero vector if norm is zero."""
        norm = np.linalg.norm(vec)
        if norm == 0:
            return vec
        return vec / norm
