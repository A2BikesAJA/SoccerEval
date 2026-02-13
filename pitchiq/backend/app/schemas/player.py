"""Player schemas."""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class PlayerCreate(BaseModel):
    team_id: int
    name: str
    jersey_number: Optional[int] = None
    position: Optional[str] = None


class PlayerResponse(BaseModel):
    id: int
    team_id: int
    name: str
    jersey_number: Optional[int] = None
    position: Optional[str] = None
    photo_url: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RosterEntry(BaseModel):
    """Single entry for roster input: jersey number to player name mapping."""
    jersey_number: int
    name: str
    position: Optional[str] = None
