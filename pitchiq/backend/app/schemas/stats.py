"""Stats and scores schemas."""

from pydantic import BaseModel
from datetime import date, datetime
from typing import Optional, Any


class PlayerGameStatsResponse(BaseModel):
    id: int
    game_player_id: int
    metric_name: str
    metric_value: float
    data_density: float
    is_extrapolated: bool

    model_config = {"from_attributes": True}


class TeamGameStatsResponse(BaseModel):
    id: int
    game_id: int
    metric_name: str
    metric_value: float

    model_config = {"from_attributes": True}


class PlayerScoreResponse(BaseModel):
    id: int
    game_player_id: int
    overall_score: float
    confidence: float
    category_scores: Optional[dict[str, Any]] = None
    bonus_events: Optional[dict[str, Any]] = None
    raw_composite: Optional[float] = None
    minutes_adjustment: float

    model_config = {"from_attributes": True}


class PIQSubAttributes(BaseModel):
    """29 sub-attributes organized by category."""
    # Speed
    sprint_speed: int = 50
    acceleration: int = 50
    off_ball_movement: int = 50
    recovery_runs: int = 50
    agility: int = 50
    # Shooting
    finishing: int = 50
    shot_power: int = 50
    long_shots: int = 50
    positioning: int = 50
    volleys_headers: int = 50
    # Passing
    short_passing: int = 50
    long_passing: int = 50
    crossing: int = 50
    vision: int = 50
    free_kick_delivery: int = 50
    # Dribbling
    ball_control: int = 50
    dribbling: int = 50
    composure: int = 50
    flair: int = 50
    balance: int = 50
    # Defending
    standing_tackle: int = 50
    interceptions: int = 50
    heading_accuracy: int = 50
    marking: int = 50
    defensive_awareness: int = 50
    # Physicality
    stamina: int = 50
    strength: int = 50
    aggression: int = 50
    jumping: int = 50


class PIQRatingResponse(BaseModel):
    id: int
    player_id: int
    ovr: int
    spd: int
    sht: int
    pas: int
    drb: int
    def_: int
    phy: int
    sub_attributes: Optional[dict[str, Any]] = None
    competition_tier: Optional[int] = None
    level_multiplier_applied: Optional[float] = None
    games_analyzed_count: int
    confidence_level: str

    model_config = {"from_attributes": True}


class PIQRatingHistoryResponse(BaseModel):
    id: int
    player_id: int
    ovr: int
    attributes: Optional[dict[str, Any]] = None
    games_analyzed_count: int
    triggered_by_game_id: Optional[int] = None
    snapshot_date: date

    model_config = {"from_attributes": True}
