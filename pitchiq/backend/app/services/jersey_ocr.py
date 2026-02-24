from __future__ import annotations

"""Jersey number OCR service.

Reads jersey numbers from player bounding boxes using optical character
recognition with preprocessing optimised for on-field conditions (motion
blur, variable lighting, low resolution).
"""

import logging
import re
from typing import Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


class JerseyOCR:
    """Reads jersey numbers from cropped player images.

    The pipeline:
    1. Crop the torso region from the player bounding box.
    2. Pre-process (resize, contrast enhancement, adaptive thresholding).
    3. Run OCR (PaddleOCR when available, simulated fallback for MVP).
    4. Filter and score candidate numbers.
    """

    # Torso crop ratios within the player bounding box.
    TORSO_TOP_RATIO = 0.15
    TORSO_BOTTOM_RATIO = 0.55
    TORSO_LEFT_RATIO = 0.15
    TORSO_RIGHT_RATIO = 0.85

    # Resize target for the torso crop before OCR.
    OCR_INPUT_WIDTH = 128
    OCR_INPUT_HEIGHT = 128

    # Valid jersey numbers on a soccer pitch.
    MIN_JERSEY_NUMBER = 1
    MAX_JERSEY_NUMBER = 99

    def __init__(self):
        """Initialise the OCR engine."""
        self._ocr_engine = None
        self._engine_type: str = "none"
        self._initialised: bool = False

    # ------------------------------------------------------------------
    # Engine initialisation
    # ------------------------------------------------------------------

    def _ensure_engine(self) -> None:
        """Lazy-load the OCR engine on first use."""
        if self._initialised:
            return

        # Try PaddleOCR first.
        try:
            from paddleocr import PaddleOCR  # type: ignore[import-untyped]

            self._ocr_engine = PaddleOCR(
                use_angle_cls=True,
                lang="en",
                show_log=False,
                use_gpu=False,
            )
            self._engine_type = "paddleocr"
            logger.info("JerseyOCR: using PaddleOCR engine")
        except ImportError:
            logger.warning(
                "PaddleOCR not available; falling back to simulated OCR"
            )
            self._engine_type = "simulated"

        self._initialised = True

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def read_jersey_number(
        self, frame: np.ndarray, bbox: tuple[float, float, float, float]
    ) -> tuple[Optional[int], float]:
        """Read the jersey number from a player bounding box.

        Args:
            frame: The full frame as a BGR numpy array.
            bbox: Player bounding box ``(x1, y1, x2, y2)`` in pixel coords.

        Returns:
            A tuple ``(number, confidence)`` where *number* is the detected
            jersey number (1-99) or ``None``, and *confidence* is a float
            in ``[0, 1]``.
        """
        self._ensure_engine()

        torso_crop = self._crop_torso(frame, bbox)
        if torso_crop is None or torso_crop.size == 0:
            return None, 0.0

        processed = self._preprocess(torso_crop)

        if self._engine_type == "paddleocr":
            return self._read_with_paddleocr(processed)
        else:
            return self._read_simulated(processed)

    @staticmethod
    def get_confidence_level(score: float) -> str:
        """Map a numeric confidence score to a categorical level.

        Args:
            score: Confidence value in ``[0, 1]``.

        Returns:
            ``"high"`` if *score* >= 0.85, ``"medium"`` if >= 0.50, else
            ``"low"``.
        """
        if score >= settings.ocr_confidence_high:
            return "high"
        elif score >= settings.ocr_confidence_medium:
            return "medium"
        else:
            return "low"

    # ------------------------------------------------------------------
    # Image preprocessing
    # ------------------------------------------------------------------

    def _crop_torso(
        self, frame: np.ndarray, bbox: tuple[float, float, float, float]
    ) -> Optional[np.ndarray]:
        """Crop the torso region from the player bounding box.

        Args:
            frame: Full BGR frame.
            bbox: Player bounding box ``(x1, y1, x2, y2)``.

        Returns:
            Cropped BGR image of the torso, or ``None`` on failure.
        """
        x1, y1, x2, y2 = [int(v) for v in bbox]
        h = y2 - y1
        w = x2 - x1

        if h <= 0 or w <= 0:
            return None

        # Compute torso sub-region.
        ty1 = y1 + int(h * self.TORSO_TOP_RATIO)
        ty2 = y1 + int(h * self.TORSO_BOTTOM_RATIO)
        tx1 = x1 + int(w * self.TORSO_LEFT_RATIO)
        tx2 = x1 + int(w * self.TORSO_RIGHT_RATIO)

        fh, fw = frame.shape[:2]
        ty1 = max(0, min(ty1, fh - 1))
        ty2 = max(0, min(ty2, fh - 1))
        tx1 = max(0, min(tx1, fw - 1))
        tx2 = max(0, min(tx2, fw - 1))

        if ty2 <= ty1 or tx2 <= tx1:
            return None

        return frame[ty1:ty2, tx1:tx2].copy()

    def _preprocess(self, crop: np.ndarray) -> np.ndarray:
        """Apply preprocessing to improve OCR accuracy.

        Steps:
        1. Resize to a fixed dimension for consistency.
        2. Convert to grayscale.
        3. Apply CLAHE for contrast enhancement.
        4. Apply adaptive Gaussian thresholding.

        Args:
            crop: BGR image of the torso region.

        Returns:
            Preprocessed grayscale image ready for OCR.
        """
        # Resize while preserving aspect ratio with padding.
        resized = cv2.resize(
            crop,
            (self.OCR_INPUT_WIDTH, self.OCR_INPUT_HEIGHT),
            interpolation=cv2.INTER_CUBIC,
        )

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

        # Contrast-limited adaptive histogram equalisation.
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(4, 4))
        enhanced = clahe.apply(gray)

        # Adaptive thresholding to handle variable lighting.
        thresh = cv2.adaptiveThreshold(
            enhanced,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15,
            C=5,
        )

        return thresh

    # ------------------------------------------------------------------
    # OCR backends
    # ------------------------------------------------------------------

    def _read_with_paddleocr(
        self, processed: np.ndarray
    ) -> tuple[Optional[int], float]:
        """Run PaddleOCR on a preprocessed torso image.

        Args:
            processed: Preprocessed grayscale image.

        Returns:
            ``(number, confidence)`` tuple.
        """
        # PaddleOCR expects a BGR or grayscale image.
        # Convert single-channel to 3-channel for compatibility.
        if len(processed.shape) == 2:
            ocr_input = cv2.cvtColor(processed, cv2.COLOR_GRAY2BGR)
        else:
            ocr_input = processed

        try:
            results = self._ocr_engine.ocr(ocr_input, cls=True)
        except Exception as exc:
            logger.warning("PaddleOCR inference failed: %s", exc)
            return None, 0.0

        if not results or not results[0]:
            return None, 0.0

        best_number: Optional[int] = None
        best_conf: float = 0.0

        for line in results[0]:
            # Each line: [bbox_points, (text, confidence)]
            text = line[1][0]
            conf = float(line[1][1])

            candidate = self._parse_jersey_number(text)
            if candidate is not None and conf > best_conf:
                best_number = candidate
                best_conf = conf

        return best_number, best_conf

    def _read_simulated(
        self, processed: np.ndarray
    ) -> tuple[Optional[int], float]:
        """Simulated OCR fallback for development and MVP testing.

        Uses basic image analysis heuristics to produce a plausible
        jersey number.  This should be replaced with a real OCR engine
        in production.

        Args:
            processed: Preprocessed grayscale image.

        Returns:
            ``(number, confidence)`` tuple.
        """
        # Heuristic: count the number of connected components (blobs) that
        # might be digit shapes.
        if len(processed.shape) == 3:
            binary = cv2.cvtColor(processed, cv2.COLOR_BGR2GRAY)
        else:
            binary = processed

        # Invert if the image is mostly white (digits are dark on light).
        if np.mean(binary) > 127:
            binary = cv2.bitwise_not(binary)

        num_labels, labels, stats, centroids = cv2.connectedComponentsWithStats(
            binary, connectivity=8
        )

        # Filter components by size to find digit-like blobs.
        h, w = binary.shape
        min_area = (h * w) * 0.01
        max_area = (h * w) * 0.40
        digit_blobs = []
        for i in range(1, num_labels):  # Skip background label 0
            area = stats[i, cv2.CC_STAT_AREA]
            blob_w = stats[i, cv2.CC_STAT_WIDTH]
            blob_h = stats[i, cv2.CC_STAT_HEIGHT]
            aspect_ratio = blob_h / max(blob_w, 1)
            if min_area <= area <= max_area and 0.5 <= aspect_ratio <= 5.0:
                digit_blobs.append(
                    {
                        "centroid_x": centroids[i][0],
                        "area": area,
                    }
                )

        if not digit_blobs:
            return None, 0.0

        # Sort blobs left-to-right to form a number.
        digit_blobs.sort(key=lambda b: b["centroid_x"])

        # Estimate number of digits.
        n_digits = min(len(digit_blobs), 2)

        if n_digits == 0:
            return None, 0.0

        # Use a deterministic hash of the image content to produce a
        # repeatable simulated number.
        pixel_hash = int(np.sum(binary.astype(np.int64)) % 99) + 1
        simulated_number = max(
            self.MIN_JERSEY_NUMBER,
            min(pixel_hash, self.MAX_JERSEY_NUMBER),
        )

        # Confidence is low for simulated results.
        simulated_conf = 0.30 + 0.15 * min(n_digits / 2.0, 1.0)

        logger.debug(
            "Simulated OCR: number=%d, confidence=%.2f",
            simulated_number,
            simulated_conf,
        )
        return simulated_number, simulated_conf

    # ------------------------------------------------------------------
    # Parsing helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_jersey_number(text: str) -> Optional[int]:
        """Parse a jersey number from raw OCR text.

        Filters for valid 1-2 digit numbers in the range [1, 99].

        Args:
            text: Raw text string from OCR.

        Returns:
            Integer jersey number, or ``None`` if no valid number found.
        """
        # Strip whitespace and non-digit characters.
        digits = re.findall(r"\d+", text)
        for d in digits:
            try:
                num = int(d)
                if 1 <= num <= 99:
                    return num
            except ValueError:
                continue
        return None
