from __future__ import annotations

"""Club model."""

from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship

from app.models.base import Base


class Club(Base):
    __tablename__ = "clubs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    logo_url = Column(String(512), nullable=True)

    teams = relationship("Team", back_populates="club", cascade="all, delete-orphan")
