from __future__ import annotations

"""Team schemas."""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class TeamCreate(BaseModel):
    club_id: int
    name: str
    age_group: str
    season: Optional[str] = None
    competition_tier: int = Field(ge=1, le=8, default=6)
    league_name: Optional[str] = None


class TeamResponse(BaseModel):
    id: int
    club_id: int
    name: str
    age_group: str
    season: Optional[str] = None
    competition_tier: int
    league_name: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
