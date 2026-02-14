from __future__ import annotations

"""Player Score and PIQ Rating models."""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, Date, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class PIQConfidenceLevel(str, enum.Enum):
    CALCULATING = "calculating"  # < 3 games
    PRELIMINARY = "preliminary"  # 3-5 games
    DEVELOPING = "developing"    # 6-10 games
    ESTABLISHED = "established"  # 11+ games


class PlayerScore(Base):
    """Single-game Player Score (0-10)."""
    __tablename__ = "player_scores"

    id = Column(Integer, primary_key=True, index=True)
    game_player_id = Column(Integer, ForeignKey("game_players.id"), nullable=False, unique=True)
    overall_score = Column(Float, nullable=False)
    confidence = Column(Float, default=1.0)
    category_scores = Column(JSON, nullable=True)
    bonus_events = Column(JSON, nullable=True)
    raw_composite = Column(Float, nullable=True)
    minutes_adjustment = Column(Float, default=1.0)

    game_player = relationship("GamePlayer", back_populates="score")


class PIQRating(Base):
    """Persistent cross-game PIQ Rating (1-99 OVR)."""
    __tablename__ = "piq_ratings"

    id = Column(Integer, primary_key=True, index=True)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    ovr = Column(Integer, nullable=False)
    spd = Column(Integer, nullable=False)
    sht = Column(Integer, nullable=False)
    pas = Column(Integer, nullable=False)
    drb = Column(Integer, nullable=False)
    _def = Column("def", Integer, nullable=False)
    phy = Column(Integer, nullable=False)
    sub_attributes = Column(JSON, nullable=True)
    competition_tier = Column(Integer, nullable=True)
    level_multiplier_applied = Column(Float, nullable=True)
    games_analyzed_count = Column(Integer, default=0)
    confidence_level = Column(
        SQLEnum(PIQConfidenceLevel),
        default=PIQConfidenceLevel.CALCULATING
    )

    player = relationship("Player", back_populates="piq_ratings")
    history = relationship("PIQRatingHistory", back_populates="piq_rating", cascade="all, delete-orphan")


class PIQRatingHistory(Base):
    """Snapshot of PIQ Rating for trend tracking."""
    __tablename__ = "piq_rating_history"

    id = Column(Integer, primary_key=True, index=True)
    piq_rating_id = Column(Integer, ForeignKey("piq_ratings.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    ovr = Column(Integer, nullable=False)
    attributes = Column(JSON, nullable=True)  # All 6 face-card + 29 sub-attributes
    games_analyzed_count = Column(Integer, default=0)
    triggered_by_game_id = Column(Integer, ForeignKey("games.id"), nullable=True)
    snapshot_date = Column(Date, nullable=False)

    piq_rating = relationship("PIQRating", back_populates="history")
