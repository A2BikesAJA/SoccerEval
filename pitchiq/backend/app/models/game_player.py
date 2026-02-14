from __future__ import annotations

"""GamePlayer join model — players in a specific game."""

from sqlalchemy import Column, Integer, Float, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class GamePlayer(Base):
    __tablename__ = "game_players"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=False)
    position_played = Column(String(10), nullable=True)
    minutes_played = Column(Float, default=0.0)
    started = Column(Boolean, default=False)
    screen_time_ratio = Column(Float, default=0.0)
    adjusted_screen_time_ratio = Column(Float, default=0.0)
    visible_frame_count = Column(Integer, default=0)
    total_game_frames = Column(Integer, default=0)
    identity_confidence = Column(Float, default=0.0)

    game = relationship("Game", back_populates="game_players")
    player = relationship("Player", back_populates="game_appearances")
    stats = relationship("PlayerGameStats", back_populates="game_player", cascade="all, delete-orphan")
    score = relationship("PlayerScore", back_populates="game_player", uselist=False, cascade="all, delete-orphan")
