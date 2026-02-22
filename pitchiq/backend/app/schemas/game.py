from __future__ import annotations

"""Game schemas."""

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional

from app.schemas.player import PlayerResponse, RosterEntry
from app.schemas.stats import TeamGameStatsResponse, PlayerScoreResponse


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
    match_format: Optional[str] = None
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
    match_format: Optional[str] = None
    duration_minutes: Optional[float] = None
    score_home: Optional[int] = None
    score_away: Optional[int] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class GamePlayerResponse(BaseModel):
    """A player's participation in a specific game."""
    id: int
    game_id: int
    player_id: int
    position_played: Optional[str] = None
    minutes_played: float = 0.0
    started: bool = False
    screen_time_ratio: float = 0.0
    adjusted_screen_time_ratio: float = 0.0
    visible_frame_count: int = 0
    total_game_frames: int = 0
    identity_confidence: float = 0.0
    player: Optional[PlayerResponse] = None
    score: Optional[PlayerScoreResponse] = None

    model_config = {"from_attributes": True}


class GameDetailResponse(GameResponse):
    """Extended game response with stats and players."""
    video_sources: list[GameVideoSourceResponse] = []
    team_stats: list[TeamGameStatsResponse] = []
    game_players: list[GamePlayerResponse] = []
