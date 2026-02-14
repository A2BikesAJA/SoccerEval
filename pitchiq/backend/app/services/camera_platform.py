from __future__ import annotations

"""Camera platform-specific configuration and handling.

Provides per-platform processing parameters, field coverage estimation,
zoom state detection, and user-facing camera tips for various camera
sources used in youth and amateur soccer (VEO, Trace, Pixellot, etc.).
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)


@dataclass
class PlatformConfig:
    """Processing configuration for a specific camera platform.

    These parameters are tuned per platform to optimise detection and
    tracking quality given each camera's typical resolution, field of
    view, and motion characteristics.
    """

    source_type: str
    display_name: str

    # Resolution and FPS expectations.
    expected_width: int = 1920
    expected_height: int = 1080
    expected_fps: float = 30.0

    # Field coverage (fraction of the pitch visible in a typical frame).
    typical_field_coverage: float = 0.45

    # Detection tuning.
    detection_confidence_threshold: float = 0.35
    min_player_height_ratio: float = 0.04  # fraction of frame height
    max_player_height_ratio: float = 0.45

    # OCR adjustments.
    ocr_confidence_adjustment: float = 1.0  # Multiplier applied to raw OCR score.
    ocr_viable: bool = True  # Whether jersey OCR is expected to be readable.

    # Tracking tuning.
    tracking_lost_timeout_seconds: float = 3.0
    expected_camera_motion: str = "low"  # "low", "medium", "high"

    # Ball detection.
    ball_confidence_threshold: float = 0.25
    ball_min_size_ratio: float = 0.004
    ball_max_size_ratio: float = 0.06

    # VEO-specific: whether this platform does auto-follow / pan.
    has_auto_follow: bool = False
    has_zoom: bool = False

    # Additional metadata.
    notes: str = ""


# ------------------------------------------------------------------
# Pre-defined platform presets
# ------------------------------------------------------------------

_PLATFORM_PRESETS: dict[str, PlatformConfig] = {
    "veo": PlatformConfig(
        source_type="veo",
        display_name="VEO Camera",
        expected_width=3840,
        expected_height=2160,
        expected_fps=30.0,
        typical_field_coverage=0.45,
        detection_confidence_threshold=0.35,
        ocr_confidence_adjustment=0.90,
        ocr_viable=True,
        tracking_lost_timeout_seconds=3.0,
        expected_camera_motion="medium",
        has_auto_follow=True,
        has_zoom=True,
        notes="180-degree lens; auto-follow mode pans and zooms to track play.",
    ),
    "veo_follow": PlatformConfig(
        source_type="veo_follow",
        display_name="VEO Follow Cam",
        expected_width=1920,
        expected_height=1080,
        expected_fps=30.0,
        typical_field_coverage=0.40,
        detection_confidence_threshold=0.35,
        ocr_confidence_adjustment=0.85,
        ocr_viable=True,
        tracking_lost_timeout_seconds=2.5,
        expected_camera_motion="high",
        has_auto_follow=True,
        has_zoom=True,
        notes="Cropped follow-cam output; higher camera motion reduces OCR accuracy.",
    ),
    "veo_panoramic": PlatformConfig(
        source_type="veo_panoramic",
        display_name="VEO Panoramic",
        expected_width=3840,
        expected_height=1080,
        expected_fps=30.0,
        typical_field_coverage=0.95,
        detection_confidence_threshold=0.30,
        min_player_height_ratio=0.02,
        ocr_confidence_adjustment=0.60,
        ocr_viable=False,
        tracking_lost_timeout_seconds=4.0,
        expected_camera_motion="low",
        has_auto_follow=False,
        has_zoom=False,
        notes="Full panoramic view; players are small, OCR unreliable.",
    ),
    "trace": PlatformConfig(
        source_type="trace",
        display_name="Trace Camera",
        expected_width=1920,
        expected_height=1080,
        expected_fps=30.0,
        typical_field_coverage=0.50,
        detection_confidence_threshold=0.35,
        ocr_confidence_adjustment=0.85,
        ocr_viable=True,
        tracking_lost_timeout_seconds=3.0,
        expected_camera_motion="medium",
        has_auto_follow=True,
        has_zoom=True,
        notes="Auto-tracking follow cam; similar to VEO follow mode.",
    ),
    "pixellot": PlatformConfig(
        source_type="pixellot",
        display_name="Pixellot Camera",
        expected_width=3840,
        expected_height=2160,
        expected_fps=25.0,
        typical_field_coverage=0.90,
        detection_confidence_threshold=0.30,
        min_player_height_ratio=0.02,
        ocr_confidence_adjustment=0.65,
        ocr_viable=False,
        tracking_lost_timeout_seconds=4.0,
        expected_camera_motion="low",
        has_auto_follow=False,
        has_zoom=False,
        notes="Fixed wide-angle; good coverage but low player resolution.",
    ),
    "sideline": PlatformConfig(
        source_type="sideline",
        display_name="Sideline Camera",
        expected_width=1920,
        expected_height=1080,
        expected_fps=30.0,
        typical_field_coverage=0.35,
        detection_confidence_threshold=0.40,
        ocr_confidence_adjustment=1.0,
        ocr_viable=True,
        tracking_lost_timeout_seconds=2.0,
        expected_camera_motion="high",
        has_auto_follow=False,
        has_zoom=False,
        notes="Handheld or tripod sideline; variable framing, high motion.",
    ),
    "broadcast": PlatformConfig(
        source_type="broadcast",
        display_name="Broadcast TV",
        expected_width=1920,
        expected_height=1080,
        expected_fps=30.0,
        typical_field_coverage=0.35,
        detection_confidence_threshold=0.35,
        ocr_confidence_adjustment=1.0,
        ocr_viable=True,
        tracking_lost_timeout_seconds=2.0,
        expected_camera_motion="high",
        has_auto_follow=False,
        has_zoom=True,
        notes="Professional broadcast; frequent cuts and zooms.",
    ),
    "drone": PlatformConfig(
        source_type="drone",
        display_name="Drone / Aerial",
        expected_width=3840,
        expected_height=2160,
        expected_fps=30.0,
        typical_field_coverage=0.80,
        detection_confidence_threshold=0.30,
        min_player_height_ratio=0.015,
        ocr_confidence_adjustment=0.50,
        ocr_viable=False,
        tracking_lost_timeout_seconds=4.0,
        expected_camera_motion="medium",
        has_auto_follow=False,
        has_zoom=False,
        notes="Top-down or angled aerial; good coverage, poor OCR.",
    ),
    "unknown": PlatformConfig(
        source_type="unknown",
        display_name="Unknown Camera",
        expected_width=1920,
        expected_height=1080,
        expected_fps=30.0,
        typical_field_coverage=0.45,
        detection_confidence_threshold=0.35,
        ocr_confidence_adjustment=0.80,
        ocr_viable=True,
        tracking_lost_timeout_seconds=3.0,
        expected_camera_motion="medium",
        notes="Default configuration for unidentified camera sources.",
    ),
}


class CameraPlatformHandler:
    """Provides camera platform-specific processing configuration.

    Supports VEO, Trace, Pixellot, sideline, broadcast, and drone
    camera types with per-platform tuning of detection, tracking,
    and OCR parameters.
    """

    def __init__(self):
        """Initialise with built-in platform presets."""
        self._presets = dict(_PLATFORM_PRESETS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_platform_config(self, source_type: str) -> PlatformConfig:
        """Return the processing configuration for a camera platform.

        Args:
            source_type: Camera platform identifier (e.g., ``"veo"``,
                ``"trace"``, ``"pixellot"``, ``"sideline"``).

        Returns:
            A ``PlatformConfig`` with all tuned processing parameters.
        """
        key = source_type.lower().strip()
        config = self._presets.get(key)
        if config is None:
            logger.warning(
                "Unknown camera platform '%s'; using default config", source_type
            )
            config = self._presets["unknown"]
        return config

    def estimate_field_coverage(self, source_type: str) -> float:
        """Estimate the fraction of the pitch visible for a given platform.

        Args:
            source_type: Camera platform identifier.

        Returns:
            Float in ``[0, 1]`` representing estimated field coverage.
        """
        config = self.get_platform_config(source_type)
        return config.typical_field_coverage

    def detect_zoom_state(
        self,
        frame: np.ndarray,
        prev_frame: Optional[np.ndarray] = None,
    ) -> float:
        """Estimate the current zoom level of the camera.

        Uses optical flow magnitude between consecutive frames to detect
        camera zoom transitions.  Higher average flow divergence from the
        frame centre indicates zooming.

        Args:
            frame: Current BGR frame.
            prev_frame: Previous BGR frame, or ``None`` for single-frame
                estimation.

        Returns:
            Estimated zoom level as a float.  ``1.0`` indicates no zoom
            (wide), higher values indicate more zoom (tighter shot).
            Without a previous frame, uses a heuristic based on average
            detected feature size.
        """
        if prev_frame is None:
            return self._estimate_zoom_from_single_frame(frame)

        return self._estimate_zoom_from_flow(frame, prev_frame)

    def get_camera_tips(self, source_type: str) -> list[str]:
        """Return user-facing tips for getting the best results from a camera.

        Args:
            source_type: Camera platform identifier.

        Returns:
            List of human-readable tip strings.
        """
        config = self.get_platform_config(source_type)
        tips: list[str] = []

        # General tips based on platform properties.
        if config.expected_camera_motion == "high":
            tips.append(
                "This camera source has significant motion. Results may be "
                "improved by using a tripod or stabiliser."
            )

        if not config.ocr_viable:
            tips.append(
                "Jersey number OCR is unreliable for this camera type due to "
                "low player resolution. Manual jersey assignment is recommended."
            )
        elif config.ocr_confidence_adjustment < 0.80:
            tips.append(
                "Jersey number OCR accuracy is reduced for this camera type. "
                "Verify auto-detected numbers in the review screen."
            )

        if config.typical_field_coverage < 0.40:
            tips.append(
                "This camera typically covers less than 40% of the field. "
                "Player statistics will be extrapolated for off-screen time."
            )

        if config.typical_field_coverage >= 0.85:
            tips.append(
                "This camera provides excellent field coverage. Player "
                "tracking will be highly reliable."
            )

        # Platform-specific tips.
        if config.source_type in ("veo", "veo_follow"):
            tips.extend([
                "For best results with VEO, ensure the camera is positioned "
                "at midfield and elevated at least 3 metres.",
                "VEO's auto-follow mode may lose players during set pieces. "
                "Consider using the panoramic export for dead-ball situations.",
            ])

        if config.source_type == "veo_panoramic":
            tips.append(
                "The panoramic view captures the full field but players appear "
                "small. Detection quality is good but OCR will not be available."
            )

        if config.source_type == "trace":
            tips.append(
                "Trace cameras work best when the full field is within the "
                "camera's tracking zone."
            )

        if config.source_type == "pixellot":
            tips.append(
                "Pixellot provides wide coverage. For best results, upload "
                "the 4K panoramic output rather than the auto-produced follow cam."
            )

        if config.source_type == "sideline":
            tips.extend([
                "Sideline footage works best when shot from the halfway line "
                "at a slight elevation.",
                "Avoid excessive panning; slow, smooth camera movements "
                "improve tracking accuracy.",
            ])

        if config.source_type == "drone":
            tips.append(
                "Drone footage should be shot from a consistent altitude of "
                "20-40 metres for optimal player detection."
            )

        if not tips:
            tips.append(
                "Ensure the video is well-lit and the field markings are "
                "visible for best calibration results."
            )

        return tips

    def get_available_platforms(self) -> list[str]:
        """Return a list of all supported platform identifiers."""
        return [k for k in self._presets.keys() if k != "unknown"]

    # ------------------------------------------------------------------
    # VEO-specific analysis
    # ------------------------------------------------------------------

    def analyze_veo_follow_motion(
        self,
        frames: list[np.ndarray],
        sample_interval: int = 5,
    ) -> dict:
        """Analyse camera motion patterns in VEO follow-cam footage.

        Detects periods of high camera motion (pans, zooms) that may
        affect detection and OCR quality.

        Args:
            frames: List of BGR frames (or a representative sample).
            sample_interval: Process every Nth frame.

        Returns:
            Dictionary with motion analysis results:
            - ``avg_motion``: Mean optical flow magnitude.
            - ``high_motion_frames``: Indices of frames with high motion.
            - ``zoom_events``: Approximate frame indices of zoom changes.
        """
        if len(frames) < 2:
            return {
                "avg_motion": 0.0,
                "high_motion_frames": [],
                "zoom_events": [],
            }

        motion_magnitudes: list[float] = []
        high_motion_frames: list[int] = []
        zoom_events: list[int] = []

        prev_gray = cv2.cvtColor(frames[0], cv2.COLOR_BGR2GRAY)

        for i in range(sample_interval, len(frames), sample_interval):
            curr_gray = cv2.cvtColor(frames[i], cv2.COLOR_BGR2GRAY)

            # Compute dense optical flow.
            flow = cv2.calcOpticalFlowFarneback(
                prev_gray,
                curr_gray,
                None,
                pyr_scale=0.5,
                levels=3,
                winsize=15,
                iterations=3,
                poly_n=5,
                poly_sigma=1.2,
                flags=0,
            )

            magnitude = np.sqrt(flow[..., 0] ** 2 + flow[..., 1] ** 2)
            avg_mag = float(np.mean(magnitude))
            motion_magnitudes.append(avg_mag)

            # High motion threshold.
            if avg_mag > 5.0:
                high_motion_frames.append(i)

            # Zoom detection: check flow divergence from centre.
            h, w = flow.shape[:2]
            cx, cy = w // 2, h // 2
            centre_region = flow[
                cy - h // 4 : cy + h // 4,
                cx - w // 4 : cx + w // 4,
            ]
            if centre_region.size > 0:
                # Radial flow indicates zoom.
                radial_mag = float(np.mean(np.abs(centre_region)))
                if radial_mag > 3.0:
                    zoom_events.append(i)

            prev_gray = curr_gray

        avg_motion = float(np.mean(motion_magnitudes)) if motion_magnitudes else 0.0

        return {
            "avg_motion": avg_motion,
            "high_motion_frames": high_motion_frames,
            "zoom_events": zoom_events,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _estimate_zoom_from_single_frame(self, frame: np.ndarray) -> float:
        """Estimate zoom level from a single frame using feature density.

        More features per unit area in the frame centre suggests a wider
        (less zoomed) shot.

        Args:
            frame: BGR image.

        Returns:
            Estimated zoom level (1.0 = wide, higher = more zoomed).
        """
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Detect keypoints using FAST.
        try:
            fast = cv2.FastFeatureDetector_create(threshold=20)
            keypoints = fast.detect(gray, None)
        except Exception:
            return 1.0

        h, w = gray.shape
        total_area = h * w
        if total_area == 0:
            return 1.0

        feature_density = len(keypoints) / (total_area / 1e6)

        # Empirical mapping: ~200 features/Mpx = wide, ~50 = zoomed.
        if feature_density >= 200:
            return 1.0
        elif feature_density <= 50:
            return 3.0
        else:
            # Linear interpolation.
            return 1.0 + 2.0 * (200 - feature_density) / 150

    def _estimate_zoom_from_flow(
        self, frame: np.ndarray, prev_frame: np.ndarray
    ) -> float:
        """Estimate zoom level change using optical flow divergence.

        Args:
            frame: Current BGR frame.
            prev_frame: Previous BGR frame.

        Returns:
            Zoom level estimate (1.0 = no change, >1 = zooming in,
            <1 = zooming out).
        """
        curr_gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        prev_gray = cv2.cvtColor(prev_frame, cv2.COLOR_BGR2GRAY)

        flow = cv2.calcOpticalFlowFarneback(
            prev_gray,
            curr_gray,
            None,
            pyr_scale=0.5,
            levels=3,
            winsize=15,
            iterations=3,
            poly_n=5,
            poly_sigma=1.2,
            flags=0,
        )

        h, w = flow.shape[:2]
        cx, cy = w / 2.0, h / 2.0

        # Create coordinate grids relative to centre.
        y_coords, x_coords = np.mgrid[0:h, 0:w]
        dx = x_coords - cx
        dy = y_coords - cy

        # Radial distance from centre.
        r = np.sqrt(dx ** 2 + dy ** 2)
        r[r == 0] = 1.0

        # Radial component of flow.
        flow_radial = (flow[..., 0] * dx + flow[..., 1] * dy) / r

        avg_radial = float(np.mean(flow_radial))

        # Positive radial flow = zooming out, negative = zooming in.
        zoom = 1.0 - avg_radial * 0.01

        return float(np.clip(zoom, 0.5, 3.0))
