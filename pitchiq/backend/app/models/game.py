from __future__ import annotations

"""Game and GameVideoSource models."""

from sqlalchemy import Column, Integer, String, ForeignKey, Date, Boolean, Float, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class GameStatus(str, enum.Enum):
    PENDING = "pending"
    UPLOADING = "uploading"
    TRANSCODING = "transcoding"
    PROCESSING = "processing"
    COMPLETED = "completed"
    ERROR = "error"


class CameraSourceType(str, enum.Enum):
    VEO_FOLLOWCAM = "veo_followcam"
    VEO_PANORAMIC = "veo_panoramic"
    TRACE = "trace"
    PIXELLOT = "pixellot"
    SIDELINE = "sideline"
    STATIC_ELEVATED = "static_elevated"
    OTHER = "other"


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    opponent_name = Column(String(255), nullable=False)
    game_date = Column(Date, nullable=False)
    age_group = Column(String(10), nullable=True)
    formation = Column(String(20), nullable=True)
    video_path = Column(String(512), nullable=True)
    status = Column(SQLEnum(GameStatus), default=GameStatus.PENDING)
    score_home = Column(Integer, nullable=True)
    score_away = Column(Integer, nullable=True)
    duration_minutes = Column(Float, nullable=True)
    match_format = Column(String(10), nullable=True)  # e.g. "5v5", "7v7", "9v9", "11v11"

    team = relationship("Team", back_populates="games")
    video_sources = relationship("GameVideoSource", back_populates="game", cascade="all, delete-orphan")
    game_players = relationship("GamePlayer", back_populates="game", cascade="all, delete-orphan")
    team_stats = relationship("TeamGameStats", back_populates="game", cascade="all, delete-orphan")
    tracking_events = relationship("TrackingEvent", back_populates="game", cascade="all, delete-orphan")
    processing_jobs = relationship("ProcessingJob", back_populates="game", cascade="all, delete-orphan")


class GameVideoSource(Base):
    __tablename__ = "game_video_sources"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    source_type = Column(SQLEnum(CameraSourceType), nullable=False)
    video_path = Column(String(512), nullable=False)
    is_primary = Column(Boolean, default=True)
    resolution = Column(String(20), nullable=True)
    fps = Column(Float, nullable=True)
    temporal_offset_ms = Column(Integer, default=0)
    field_coverage_pct = Column(Float, nullable=True)

    game = relationship("Game", back_populates="video_sources")
