from __future__ import annotations

"""Tracking event model."""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.models.base import Base


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    event_type = Column(String(50), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id"), nullable=True)
    timestamp_seconds = Column(Float, nullable=False)
    x_position = Column(Float, nullable=True)
    y_position = Column(Float, nullable=True)
    event_data = Column("metadata", JSON, nullable=True)
    source_video_id = Column(Integer, ForeignKey("game_video_sources.id"), nullable=True)

    game = relationship("Game", back_populates="tracking_events")
