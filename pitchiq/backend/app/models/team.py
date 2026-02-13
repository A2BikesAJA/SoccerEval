"""Team model."""

from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class AgeGroup(str, enum.Enum):
    U8 = "U8"
    U9 = "U9"
    U10 = "U10"
    U11 = "U11"
    U12 = "U12"
    U13 = "U13"
    U14 = "U14"
    U15 = "U15"
    U16 = "U16"
    U17 = "U17"
    U18 = "U18"
    U19 = "U19"


class CompetitionTier(int, enum.Enum):
    TIER_1 = 1  # MLS NEXT / ECNL
    TIER_2 = 2  # MLS NEXT (non-MLS) / GA
    TIER_3 = 3  # ECRL / GA Aspire / DPL
    TIER_4 = 4  # NPL / USYS NL
    TIER_5 = 5  # State Premier
    TIER_6 = 6  # Competitive Travel
    TIER_7 = 7  # Recreational+
    TIER_8 = 8  # Recreational


class Team(Base):
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True, index=True)
    club_id = Column(Integer, ForeignKey("clubs.id"), nullable=False)
    name = Column(String(255), nullable=False)
    age_group = Column(SQLEnum(AgeGroup), nullable=False)
    season = Column(String(20), nullable=True)
    competition_tier = Column(Integer, default=6)
    league_name = Column(String(255), nullable=True)

    club = relationship("Club", back_populates="teams")
    players = relationship("Player", back_populates="team", cascade="all, delete-orphan")
    games = relationship("Game", back_populates="team", cascade="all, delete-orphan")
