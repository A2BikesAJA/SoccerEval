from __future__ import annotations

"""Player and Team game statistics models."""

from sqlalchemy import Column, Integer, Float, Boolean, String, ForeignKey
from sqlalchemy.orm import relationship

from app.models.base import Base


class PlayerGameStats(Base):
    __tablename__ = "player_game_stats"

    id = Column(Integer, primary_key=True, index=True)
    game_player_id = Column(Integer, ForeignKey("game_players.id"), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)
    data_density = Column(Float, default=1.0)
    is_extrapolated = Column(Boolean, default=False)

    game_player = relationship("GamePlayer", back_populates="stats")


class TeamGameStats(Base):
    __tablename__ = "team_game_stats"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    metric_name = Column(String(100), nullable=False)
    metric_value = Column(Float, nullable=False)

    game = relationship("Game", back_populates="team_stats")
