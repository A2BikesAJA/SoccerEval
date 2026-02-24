from __future__ import annotations

"""Pitch calibration service.

Detects field lines in video frames, computes a homography mapping from
pixel coordinates to real-world pitch coordinates (in metres), and provides
distance estimation.
"""

import logging
from dataclasses import dataclass
from typing import Optional

import cv2
import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# Standard FIFA pitch dimensions in metres.
PITCH_LENGTH_M = 105.0
PITCH_WIDTH_M = 68.0

# Key pitch landmarks in real-world coordinates (metres), origin at
# bottom-left corner.  Used for homography computation.
PITCH_LANDMARKS = {
    "center_spot": (52.5, 34.0),
    "center_circle_top": (52.5, 43.15),
    "center_circle_bottom": (52.5, 24.85),
    "left_penalty_spot": (11.0, 34.0),
    "right_penalty_spot": (94.0, 34.0),
    "top_left_corner": (0.0, 68.0),
    "top_right_corner": (105.0, 68.0),
    "bottom_left_corner": (0.0, 0.0),
    "bottom_right_corner": (105.0, 0.0),
    "left_goal_top": (0.0, 37.66),
    "left_goal_bottom": (0.0, 30.34),
    "right_goal_top": (105.0, 37.66),
    "right_goal_bottom": (105.0, 30.34),
    "left_box_top_right": (16.5, 54.16),
    "left_box_bottom_right": (16.5, 13.84),
    "right_box_top_left": (88.5, 54.16),
    "right_box_bottom_left": (88.5, 13.84),
    "halfway_top": (52.5, 68.0),
    "halfway_bottom": (52.5, 0.0),
}


@dataclass
class LineSegment:
    """A detected line segment in pixel space."""

    x1: float
    y1: float
    x2: float
    y2: float
    angle_deg: float  # Orientation in degrees [0, 180)
    length: float  # Length in pixels


class PitchCalibrator:
    """Computes pixel-to-pitch coordinate transformations.

    Pipeline:
    1. Detect field lines using Hough transform on edge-detected frames.
    2. Classify lines as horizontal (touchlines, penalty box) or vertical
       (goal lines, halfway line).
    3. Find intersections to identify key pitch landmarks.
    4. Compute homography from matched pixel-pitch point pairs.
    5. Provide coordinate transformation and distance estimation.

    Falls back to a relative positioning model when not enough lines are
    detected for a reliable homography.
    """

    # Hough transform parameters.
    CANNY_LOW = 50
    CANNY_HIGH = 150
    HOUGH_RHO = 1.0
    HOUGH_THETA = np.pi / 180.0
    HOUGH_THRESHOLD = 80
    HOUGH_MIN_LINE_LENGTH = 80
    HOUGH_MAX_LINE_GAP = 15

    # Minimum number of matched point pairs for homography.
    MIN_POINTS_FOR_HOMOGRAPHY = 4

    # Angle thresholds for classifying lines.
    HORIZONTAL_ANGLE_TOLERANCE = 20.0  # degrees from 0/180
    VERTICAL_ANGLE_TOLERANCE = 20.0  # degrees from 90

    def __init__(self):
        """Initialise the pitch calibrator."""
        self._homography: Optional[np.ndarray] = None
        self._inverse_homography: Optional[np.ndarray] = None
        self._calibrated: bool = False
        self._frame_shape: Optional[tuple[int, int]] = None
        self._detected_lines: list[LineSegment] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def detect_field_lines(self, frame: np.ndarray) -> list[LineSegment]:
        """Detect field line segments in a video frame.

        Uses Canny edge detection followed by the probabilistic Hough
        transform to find line segments.  Lines are filtered by length
        and classified by orientation.

        Args:
            frame: BGR image as a numpy array.

        Returns:
            List of ``LineSegment`` objects.
        """
        self._frame_shape = frame.shape[:2]

        # Convert to grayscale and enhance field markings.
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Apply Gaussian blur to reduce noise.
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)

        # Field mask: white lines on green field.
        # Boost white regions that are likely field markings.
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        # Green field mask.
        lower_green = np.array([30, 30, 30])
        upper_green = np.array([90, 255, 255])
        field_mask = cv2.inRange(hsv, lower_green, upper_green)

        # Dilate field mask to include nearby pixels.
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
        field_mask = cv2.dilate(field_mask, kernel, iterations=2)

        # Apply field mask to focus edge detection on the field area.
        masked_gray = cv2.bitwise_and(blurred, blurred, mask=field_mask)

        # Canny edge detection.
        edges = cv2.Canny(
            masked_gray, self.CANNY_LOW, self.CANNY_HIGH, apertureSize=3
        )

        # Probabilistic Hough Line Transform.
        raw_lines = cv2.HoughLinesP(
            edges,
            rho=self.HOUGH_RHO,
            theta=self.HOUGH_THETA,
            threshold=self.HOUGH_THRESHOLD,
            minLineLength=self.HOUGH_MIN_LINE_LENGTH,
            maxLineGap=self.HOUGH_MAX_LINE_GAP,
        )

        segments: list[LineSegment] = []
        if raw_lines is None:
            logger.warning("No field lines detected in frame")
            self._detected_lines = segments
            return segments

        for line in raw_lines:
            x1, y1, x2, y2 = line[0]
            length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
            angle = np.degrees(np.arctan2(y2 - y1, x2 - x1)) % 180.0

            segments.append(
                LineSegment(
                    x1=float(x1),
                    y1=float(y1),
                    x2=float(x2),
                    y2=float(y2),
                    angle_deg=angle,
                    length=length,
                )
            )

        # Merge nearby parallel lines.
        segments = self._merge_similar_lines(segments)

        self._detected_lines = segments
        logger.info("Detected %d field line segments", len(segments))
        return segments

    def compute_homography(
        self,
        field_lines: list[LineSegment],
        manual_points: Optional[list[tuple[tuple[float, float], tuple[float, float]]]] = None,
    ) -> Optional[np.ndarray]:
        """Compute a 3x3 homography matrix from field lines or manual point pairs.

        If ``manual_points`` is provided, those are used directly.
        Otherwise the method attempts to find intersections of detected
        lines and match them to known pitch landmarks.

        Args:
            field_lines: Line segments from ``detect_field_lines``.
            manual_points: Optional list of ``(pixel_point, pitch_point)``
                tuples for direct calibration.

        Returns:
            A 3x3 homography matrix, or ``None`` if calibration failed.
        """
        if manual_points and len(manual_points) >= self.MIN_POINTS_FOR_HOMOGRAPHY:
            pixel_pts = np.array(
                [p[0] for p in manual_points], dtype=np.float64
            )
            pitch_pts = np.array(
                [p[1] for p in manual_points], dtype=np.float64
            )
            H, mask = cv2.findHomography(pixel_pts, pitch_pts, cv2.RANSAC, 5.0)
            if H is not None:
                self._homography = H
                self._inverse_homography = np.linalg.inv(H)
                self._calibrated = True
                logger.info("Homography computed from %d manual points", len(manual_points))
                return H

        # Automatic calibration from line intersections.
        intersections = self._find_intersections(field_lines)

        if len(intersections) < self.MIN_POINTS_FOR_HOMOGRAPHY:
            logger.warning(
                "Only %d intersections found; need at least %d for homography. "
                "Falling back to relative positioning.",
                len(intersections),
                self.MIN_POINTS_FOR_HOMOGRAPHY,
            )
            self._apply_fallback_homography()
            return self._homography

        # Match intersections to pitch landmarks.
        matched = self._match_intersections_to_landmarks(intersections)

        if len(matched) < self.MIN_POINTS_FOR_HOMOGRAPHY:
            logger.warning(
                "Only %d landmark matches; falling back to relative positioning.",
                len(matched),
            )
            self._apply_fallback_homography()
            return self._homography

        pixel_pts = np.array([m[0] for m in matched], dtype=np.float64)
        pitch_pts = np.array([m[1] for m in matched], dtype=np.float64)

        H, mask = cv2.findHomography(pixel_pts, pitch_pts, cv2.RANSAC, 5.0)
        if H is None:
            logger.warning("Homography computation failed; using fallback")
            self._apply_fallback_homography()
            return self._homography

        self._homography = H
        self._inverse_homography = np.linalg.inv(H)
        self._calibrated = True
        inliers = int(mask.sum()) if mask is not None else len(matched)
        logger.info(
            "Homography computed with %d/%d inliers", inliers, len(matched)
        )
        return H

    def pixel_to_pitch(
        self,
        pixel_coords: tuple[float, float],
        homography: Optional[np.ndarray] = None,
    ) -> tuple[float, float]:
        """Transform pixel coordinates to real-world pitch coordinates.

        Args:
            pixel_coords: ``(x, y)`` in pixel space.
            homography: Optional 3x3 matrix.  Uses the internally stored
                homography if not provided.

        Returns:
            ``(x_metres, y_metres)`` on the pitch.
        """
        H = homography if homography is not None else self._homography
        if H is None:
            # Fallback: return normalised relative position.
            return self._pixel_to_relative(pixel_coords)

        pt = np.array([pixel_coords[0], pixel_coords[1], 1.0], dtype=np.float64)
        transformed = H @ pt
        if abs(transformed[2]) < 1e-10:
            return self._pixel_to_relative(pixel_coords)

        x = transformed[0] / transformed[2]
        y = transformed[1] / transformed[2]

        # Clamp to pitch bounds.
        x = float(np.clip(x, 0.0, PITCH_LENGTH_M))
        y = float(np.clip(y, 0.0, PITCH_WIDTH_M))

        return (x, y)

    def estimate_distance(
        self,
        point1: tuple[float, float],
        point2: tuple[float, float],
        homography: Optional[np.ndarray] = None,
    ) -> float:
        """Estimate the real-world distance between two pixel points.

        Both points are transformed to pitch coordinates and the Euclidean
        distance is computed.

        Args:
            point1: First point ``(x, y)`` in pixel space.
            point2: Second point ``(x, y)`` in pixel space.
            homography: Optional 3x3 matrix.

        Returns:
            Distance in metres.
        """
        p1 = self.pixel_to_pitch(point1, homography)
        p2 = self.pixel_to_pitch(point2, homography)
        return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))

    @property
    def is_calibrated(self) -> bool:
        """Return whether a homography has been successfully computed."""
        return self._calibrated

    @property
    def homography_matrix(self) -> Optional[np.ndarray]:
        """Return the current homography matrix."""
        return self._homography

    # ------------------------------------------------------------------
    # Line processing helpers
    # ------------------------------------------------------------------

    def _merge_similar_lines(
        self, lines: list[LineSegment], angle_tol: float = 5.0, dist_tol: float = 20.0
    ) -> list[LineSegment]:
        """Merge line segments that are nearly parallel and close together.

        Args:
            lines: Raw line segments.
            angle_tol: Maximum angle difference (degrees) for merging.
            dist_tol: Maximum perpendicular distance (pixels) for merging.

        Returns:
            De-duplicated list of line segments.
        """
        if len(lines) <= 1:
            return lines

        merged: list[LineSegment] = []
        used = [False] * len(lines)

        for i in range(len(lines)):
            if used[i]:
                continue

            cluster_xs = [lines[i].x1, lines[i].x2]
            cluster_ys = [lines[i].y1, lines[i].y2]
            cluster_angles = [lines[i].angle_deg]

            for j in range(i + 1, len(lines)):
                if used[j]:
                    continue

                angle_diff = abs(lines[i].angle_deg - lines[j].angle_deg)
                angle_diff = min(angle_diff, 180.0 - angle_diff)

                if angle_diff > angle_tol:
                    continue

                # Perpendicular distance between midpoints.
                mid_i = (
                    (lines[i].x1 + lines[i].x2) / 2,
                    (lines[i].y1 + lines[i].y2) / 2,
                )
                mid_j = (
                    (lines[j].x1 + lines[j].x2) / 2,
                    (lines[j].y1 + lines[j].y2) / 2,
                )
                dist = np.sqrt(
                    (mid_i[0] - mid_j[0]) ** 2 + (mid_i[1] - mid_j[1]) ** 2
                )

                if dist <= dist_tol:
                    cluster_xs.extend([lines[j].x1, lines[j].x2])
                    cluster_ys.extend([lines[j].y1, lines[j].y2])
                    cluster_angles.append(lines[j].angle_deg)
                    used[j] = True

            used[i] = True

            # Create a merged line from the cluster extremes.
            avg_angle = float(np.mean(cluster_angles))
            if abs(avg_angle - 90) < 45:
                # Roughly vertical: sort by Y.
                pts = sorted(zip(cluster_xs, cluster_ys), key=lambda p: p[1])
            else:
                # Roughly horizontal: sort by X.
                pts = sorted(zip(cluster_xs, cluster_ys), key=lambda p: p[0])

            sx, sy = pts[0]
            ex, ey = pts[-1]
            length = np.sqrt((ex - sx) ** 2 + (ey - sy) ** 2)
            merged.append(
                LineSegment(
                    x1=sx, y1=sy, x2=ex, y2=ey,
                    angle_deg=avg_angle, length=length,
                )
            )

        return merged

    def _find_intersections(
        self, lines: list[LineSegment]
    ) -> list[tuple[float, float]]:
        """Find intersection points of nearly-perpendicular line pairs.

        Args:
            lines: Detected line segments.

        Returns:
            List of ``(x, y)`` intersection points in pixel space.
        """
        intersections: list[tuple[float, float]] = []

        horizontals = [
            l for l in lines
            if l.angle_deg < self.HORIZONTAL_ANGLE_TOLERANCE
            or l.angle_deg > (180.0 - self.HORIZONTAL_ANGLE_TOLERANCE)
        ]
        verticals = [
            l for l in lines
            if abs(l.angle_deg - 90.0) < self.VERTICAL_ANGLE_TOLERANCE
        ]

        for h_line in horizontals:
            for v_line in verticals:
                pt = self._line_intersection(
                    (h_line.x1, h_line.y1, h_line.x2, h_line.y2),
                    (v_line.x1, v_line.y1, v_line.x2, v_line.y2),
                )
                if pt is not None:
                    # Check that the intersection is near the actual segments.
                    if self._frame_shape is not None:
                        fh, fw = self._frame_shape
                        if 0 <= pt[0] <= fw and 0 <= pt[1] <= fh:
                            intersections.append(pt)

        # De-duplicate close intersections.
        return self._deduplicate_points(intersections, min_dist=15.0)

    @staticmethod
    def _line_intersection(
        line1: tuple[float, float, float, float],
        line2: tuple[float, float, float, float],
    ) -> Optional[tuple[float, float]]:
        """Compute the intersection of two lines (extended to infinity).

        Args:
            line1: ``(x1, y1, x2, y2)`` first line.
            line2: ``(x1, y1, x2, y2)`` second line.

        Returns:
            ``(x, y)`` intersection point, or ``None`` if lines are parallel.
        """
        x1, y1, x2, y2 = line1
        x3, y3, x4, y4 = line2

        denom = (x1 - x2) * (y3 - y4) - (y1 - y2) * (x3 - x4)
        if abs(denom) < 1e-10:
            return None

        t = ((x1 - x3) * (y3 - y4) - (y1 - y3) * (x3 - x4)) / denom
        ix = x1 + t * (x2 - x1)
        iy = y1 + t * (y2 - y1)

        return (float(ix), float(iy))

    @staticmethod
    def _deduplicate_points(
        points: list[tuple[float, float]], min_dist: float = 15.0
    ) -> list[tuple[float, float]]:
        """Remove near-duplicate points, keeping the first occurrence."""
        unique: list[tuple[float, float]] = []
        for pt in points:
            is_dup = False
            for upt in unique:
                if np.sqrt((pt[0] - upt[0]) ** 2 + (pt[1] - upt[1]) ** 2) < min_dist:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(pt)
        return unique

    def _match_intersections_to_landmarks(
        self,
        intersections: list[tuple[float, float]],
    ) -> list[tuple[tuple[float, float], tuple[float, float]]]:
        """Match detected intersections to known pitch landmarks.

        Uses a spatial heuristic: sort intersections by position in the
        frame and map them to expected landmark positions.  This is a
        simplified approach; production systems would use more sophisticated
        line classification.

        Args:
            intersections: Intersection points in pixel space.

        Returns:
            List of ``(pixel_point, pitch_point)`` pairs.
        """
        if not intersections or self._frame_shape is None:
            return []

        fh, fw = self._frame_shape

        # Sort intersections into a grid-like structure.
        # Normalise pixel positions to [0, 1].
        normalised = [
            (ix / fw, iy / fh, ix, iy) for ix, iy in intersections
        ]

        # Sort by x then y.
        normalised.sort(key=lambda p: (p[0], p[1]))

        # Map to pitch corners and key points based on spatial ordering.
        # Take the four extreme points as corner candidates.
        corner_landmarks = [
            "bottom_left_corner",
            "top_left_corner",
            "bottom_right_corner",
            "top_right_corner",
        ]

        matched: list[tuple[tuple[float, float], tuple[float, float]]] = []

        if len(normalised) >= 4:
            # Bottom-left: smallest x, largest y (bottom of frame).
            by_bl = sorted(normalised, key=lambda p: (p[0], -p[1]))
            bl = by_bl[0]
            matched.append(
                ((bl[2], bl[3]), PITCH_LANDMARKS["bottom_left_corner"])
            )

            # Top-left: smallest x, smallest y.
            by_tl = sorted(normalised, key=lambda p: (p[0], p[1]))
            tl = by_tl[0]
            if tl != bl:
                matched.append(
                    ((tl[2], tl[3]), PITCH_LANDMARKS["top_left_corner"])
                )

            # Bottom-right: largest x, largest y.
            by_br = sorted(normalised, key=lambda p: (-p[0], -p[1]))
            br = by_br[0]
            matched.append(
                ((br[2], br[3]), PITCH_LANDMARKS["bottom_right_corner"])
            )

            # Top-right: largest x, smallest y.
            by_tr = sorted(normalised, key=lambda p: (-p[0], p[1]))
            tr = by_tr[0]
            if tr != br:
                matched.append(
                    ((tr[2], tr[3]), PITCH_LANDMARKS["top_right_corner"])
                )

        # If we have a centre-ish intersection, map to halfway line.
        for nx, ny, px, py in normalised:
            if 0.4 <= nx <= 0.6 and 0.3 <= ny <= 0.7:
                matched.append(
                    ((px, py), PITCH_LANDMARKS["center_spot"])
                )
                break

        return matched

    # ------------------------------------------------------------------
    # Fallback positioning
    # ------------------------------------------------------------------

    def _apply_fallback_homography(self) -> None:
        """Set a basic affine-like homography mapping frame to full pitch.

        This is a rough estimate used when line detection fails.  It maps
        the four frame corners to the four pitch corners.
        """
        if self._frame_shape is None:
            logger.error("Cannot apply fallback homography without frame shape")
            return

        fh, fw = self._frame_shape
        pixel_pts = np.array([
            [0, fh],       # bottom-left
            [0, 0],        # top-left
            [fw, 0],       # top-right
            [fw, fh],      # bottom-right
        ], dtype=np.float64)

        pitch_pts = np.array([
            [0.0, 0.0],
            [0.0, PITCH_WIDTH_M],
            [PITCH_LENGTH_M, PITCH_WIDTH_M],
            [PITCH_LENGTH_M, 0.0],
        ], dtype=np.float64)

        H, _ = cv2.findHomography(pixel_pts, pitch_pts)
        if H is not None:
            self._homography = H
            self._inverse_homography = np.linalg.inv(H)
            self._calibrated = True
            logger.info("Applied fallback homography (full-frame to full-pitch)")
        else:
            logger.error("Fallback homography computation failed")

    def _pixel_to_relative(
        self, pixel_coords: tuple[float, float]
    ) -> tuple[float, float]:
        """Convert pixel coords to relative pitch coords without homography.

        Simply scales pixel position to pitch dimensions based on frame size.

        Args:
            pixel_coords: ``(x, y)`` in pixel space.

        Returns:
            ``(x_metres, y_metres)`` approximate pitch position.
        """
        if self._frame_shape is None:
            return (0.0, 0.0)

        fh, fw = self._frame_shape
        rel_x = pixel_coords[0] / max(fw, 1)
        rel_y = pixel_coords[1] / max(fh, 1)

        pitch_x = rel_x * PITCH_LENGTH_M
        pitch_y = (1.0 - rel_y) * PITCH_WIDTH_M  # Flip Y axis

        return (
            float(np.clip(pitch_x, 0.0, PITCH_LENGTH_M)),
            float(np.clip(pitch_y, 0.0, PITCH_WIDTH_M)),
        )
