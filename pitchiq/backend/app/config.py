from __future__ import annotations

"""Application configuration."""

from pydantic_settings import BaseSettings
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    # Application
    app_name: str = "PitchIQ"
    debug: bool = True
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "sqlite:///./data/pitchiq.db"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # File Storage
    upload_dir: Path = Path("data/uploads")
    processed_dir: Path = Path("data/processed")
    frames_dir: Path = Path("data/frames")
    max_upload_size_mb: int = 5120  # 5GB

    # Video Processing
    default_detection_fps: float = 2.0
    default_tracking_fps: float = 0.5
    transcode_resolution: str = "1280x720"
    transcode_fps: int = 30

    # CV Pipeline
    yolo_model_path: str = "yolov8x.pt"
    ocr_confidence_high: float = 0.85
    ocr_confidence_medium: float = 0.50
    reid_similarity_threshold: float = 0.80
    track_lost_threshold_seconds: float = 3.0

    # Identity Fusion Weights
    identity_weight_ocr_high: float = 10.0
    identity_weight_ocr_medium: float = 3.0
    identity_weight_appearance: float = 5.0
    identity_weight_physical: float = 2.0
    identity_weight_spatial: float = 4.0

    # PIQ Rating
    piq_min_games: int = 3
    piq_rolling_window: int = 8
    piq_recency_weights: list[float] = [1.0, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3]

    # Screen Time
    min_screen_time_for_extrapolation: float = 0.40
    screen_time_warning_threshold: float = 0.50

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    class Config:
        env_file = ".env"
        env_prefix = "PITCHIQ_"


settings = Settings()
