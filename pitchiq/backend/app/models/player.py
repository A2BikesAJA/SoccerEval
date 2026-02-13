"""Player model."""

from sqlalchemy import Column, Integer, String, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.models.base import Base


class PlayerPosition(str, enum.Enum):
    # Goalkeeper
    GK = "GK"
    # Center Back
    CB = "CB"
    SW = "SW"  # Sweeper
    # Fullback / Wingback
    LB = "LB"
    RB = "RB"
    LWB = "LWB"
    RWB = "RWB"
    # Defensive Midfielder
    CDM = "CDM"
    DM = "DM"
    # Central Midfielder
    CM = "CM"
    LCM = "LCM"
    RCM = "RCM"
    # Attacking Midfielder
    CAM = "CAM"
    AM = "AM"
    # Winger
    LW = "LW"
    RW = "RW"
    LM = "LM"
    RM = "RM"
    # Striker / Forward
    ST = "ST"
    CF = "CF"
    LF = "LF"
    RF = "RF"


# Mapping specific positions to position groups for stat weighting
POSITION_GROUP_MAP = {
    "GK": "GK",
    "CB": "CB", "SW": "CB",
    "LB": "FB", "RB": "FB", "LWB": "FB", "RWB": "FB",
    "CDM": "CDM", "DM": "CDM",
    "CM": "CM", "LCM": "CM", "RCM": "CM",
    "CAM": "CAM", "AM": "CAM",
    "LW": "W", "RW": "W", "LM": "W", "RM": "W",
    "ST": "ST", "CF": "ST", "LF": "ST", "RF": "ST",
}


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=False)
    name = Column(String(255), nullable=False)
    jersey_number = Column(Integer, nullable=True)
    position = Column(SQLEnum(PlayerPosition), nullable=True)
    photo_url = Column(String(512), nullable=True)

    team = relationship("Team", back_populates="players")
    game_appearances = relationship("GamePlayer", back_populates="player")
    piq_ratings = relationship("PIQRating", back_populates="player")
