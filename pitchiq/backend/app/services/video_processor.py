"""Video preprocessing and transcoding service."""

import subprocess
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional

from app.config import settings


@dataclass
class VideoInfo:
    width: int
    height: int
    fps: float
    duration_seconds: float
    codec: str
    file_size_mb: float


class VideoProcessor:
    """Handles video transcoding and frame extraction."""

    def __init__(self):
        self.output_dir = Path(settings.processed_dir)
        self.frames_dir = Path(settings.frames_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.frames_dir.mkdir(parents=True, exist_ok=True)

    def get_video_info(self, video_path: str) -> VideoInfo:
        """Extract video metadata using ffprobe."""
        cmd = [
            "ffprobe", "-v", "quiet", "-print_format", "json",
            "-show_format", "-show_streams", video_path
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        data = json.loads(result.stdout)

        video_stream = next(
            (s for s in data.get("streams", []) if s["codec_type"] == "video"),
            {}
        )
        fmt = data.get("format", {})

        return VideoInfo(
            width=int(video_stream.get("width", 0)),
            height=int(video_stream.get("height", 0)),
            fps=eval(video_stream.get("r_frame_rate", "30/1")),
            duration_seconds=float(fmt.get("duration", 0)),
            codec=video_stream.get("codec_name", "unknown"),
            file_size_mb=float(fmt.get("size", 0)) / (1024 * 1024),
        )

    def transcode(self, input_path: str, game_id: int) -> str:
        """Transcode video to standardized format (720p, 30fps, H.264)."""
        output_path = self.output_dir / f"game_{game_id}_processed.mp4"
        cmd = [
            "ffmpeg", "-i", input_path,
            "-vf", f"scale={settings.transcode_resolution}",
            "-r", str(settings.transcode_fps),
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            "-y", str(output_path),
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return str(output_path)

    def extract_frames(
        self,
        video_path: str,
        game_id: int,
        fps: float = None,
        start_time: float = 0,
        end_time: float = None,
    ) -> list[str]:
        """Extract frames at specified FPS for CV pipeline processing."""
        if fps is None:
            fps = settings.default_detection_fps

        frame_dir = self.frames_dir / f"game_{game_id}"
        frame_dir.mkdir(parents=True, exist_ok=True)

        cmd = [
            "ffmpeg", "-i", video_path,
            "-vf", f"fps={fps}",
        ]
        if start_time > 0:
            cmd.extend(["-ss", str(start_time)])
        if end_time:
            cmd.extend(["-to", str(end_time)])

        cmd.extend([
            "-q:v", "2",
            str(frame_dir / "frame_%06d.jpg"),
            "-y",
        ])
        subprocess.run(cmd, capture_output=True, check=True)

        frames = sorted(frame_dir.glob("frame_*.jpg"))
        return [str(f) for f in frames]

    def extract_clip(
        self,
        video_path: str,
        start_seconds: float,
        duration: float,
        output_path: str,
    ) -> str:
        """Extract a short clip for highlight reels."""
        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", str(start_seconds),
            "-t", str(duration),
            "-c:v", "libx264", "-preset", "fast",
            "-c:a", "aac",
            "-y", output_path,
        ]
        subprocess.run(cmd, capture_output=True, check=True)
        return output_path

    def estimate_field_coverage(self, video_path: str) -> float:
        """Estimate what percentage of the field is typically visible.

        Based on camera source type heuristics.
        """
        # This would use actual frame analysis in production.
        # For MVP, return heuristic based on source type.
        return 0.45  # Default: assume ~45% for Follow Cam
