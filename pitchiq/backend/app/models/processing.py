from __future__ import annotations

"""Processing job model."""

from sqlalchemy import Column, Integer, Float, String, ForeignKey, DateTime
from sqlalchemy.orm import relationship

from app.models.base import Base


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id = Column(Integer, primary_key=True, index=True)
    game_id = Column(Integer, ForeignKey("games.id"), nullable=False)
    status = Column(String(20), default="queued")  # queued, running, completed, failed
    progress_pct = Column(Float, default=0.0)
    current_stage = Column(String(50), nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(String(1000), nullable=True)

    game = relationship("Game", back_populates="processing_jobs")
