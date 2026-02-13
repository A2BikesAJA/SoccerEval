"""Game schemas."""

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

from app.schemas.player import RosterEntry


class GameVideoSourceCreate(BaseModel):
    source_type: str
    is_primary: bool = True
    resolution: Optional[str] = None
    fps: Optional[float] = None
    temporal_offset_ms: int = 0


class GameVideoSourceResponse(BaseModel):
    id: int
    game_id: int
    source_type: str
    video_path: str
    is_primary: bool
    resolution: Optional[str] = None
    fps: Optional[float] = None
    temporal_offset_ms: int
    field_coverage_pct: Optional[float] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GameCreate(BaseModel):
    team_id: int
    opponent_name: str
    game_date: date
    age_group: Optional[str] = None
    formation: Optional[str] = None
    camera_source_type: str = "other"
    roster: list[RosterEntry] = []


class GameResponse(BaseModel):
    id: int
    team_id: int
    opponent_name: str
    game_date: date
    age_group: Optional[str] = None
    formation: Optional[str] = None
    status: str
    duration_minutes: Optional[float] = None
    score_home: Optional[int] = None
    score_away: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GameDetailResponse(GameResponse):
    """Extended game response with stats and players."""
    video_sources: list[GameVideoSourceResponse] = []
    team_stats: list = []
    game_players: list = []
