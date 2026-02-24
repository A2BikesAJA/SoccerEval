from __future__ import annotations

"""Stats API routes — player and team statistics."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.models.base import get_db
from app.models.game_player import GamePlayer
from app.models.stats import PlayerGameStats, TeamGameStats
from app.models.scores import PlayerScore
from app.schemas.stats import (
    PlayerGameStatsResponse,
    TeamGameStatsResponse,
    PlayerScoreResponse,
)

router = APIRouter()


@router.get("/game/{game_id}/team", response_model=list[TeamGameStatsResponse])
def get_team_game_stats(game_id: int, db: Session = Depends(get_db)):
    """Get team-level stats for a game."""
    return db.query(TeamGameStats).filter(TeamGameStats.game_id == game_id).all()


@router.get("/game/{game_id}/players")
def get_game_player_stats(game_id: int, db: Session = Depends(get_db)):
    """Get all player stats for a game, grouped by player."""
    game_players = (
        db.query(GamePlayer)
        .options(
            joinedload(GamePlayer.player),
            joinedload(GamePlayer.stats),
            joinedload(GamePlayer.score),
        )
        .filter(GamePlayer.game_id == game_id)
        .all()
    )
    result = []
    for gp in game_players:
        stats_dict = {s.metric_name: {
            "value": s.metric_value,
            "data_density": s.data_density,
            "is_extrapolated": s.is_extrapolated,
        } for s in gp.stats}

        result.append({
            "game_player_id": gp.id,
            "player_id": gp.player_id,
            "player_name": gp.player.name if gp.player else "Unknown",
            "jersey_number": gp.player.jersey_number if gp.player else None,
            "position_played": gp.position_played,
            "minutes_played": gp.minutes_played,
            "screen_time_ratio": gp.screen_time_ratio,
            "adjusted_screen_time_ratio": gp.adjusted_screen_time_ratio,
            "identity_confidence": gp.identity_confidence,
            "stats": stats_dict,
            "score": {
                "overall_score": gp.score.overall_score,
                "confidence": gp.score.confidence,
                "category_scores": gp.score.category_scores,
                "bonus_events": gp.score.bonus_events,
            } if gp.score else None,
        })
    return result


@router.get("/player/{player_id}/history")
def get_player_stats_history(player_id: int, db: Session = Depends(get_db)):
    """Get a player's stats across all games."""
    game_players = (
        db.query(GamePlayer)
        .options(
            joinedload(GamePlayer.game),
            joinedload(GamePlayer.stats),
            joinedload(GamePlayer.score),
        )
        .filter(GamePlayer.player_id == player_id)
        .order_by(GamePlayer.id.desc())
        .all()
    )
    result = []
    for gp in game_players:
        stats_dict = {s.metric_name: s.metric_value for s in gp.stats}
        result.append({
            "game_id": gp.game_id,
            "game_date": gp.game.game_date.isoformat() if gp.game else None,
            "opponent": gp.game.opponent_name if gp.game else None,
            "position_played": gp.position_played,
            "minutes_played": gp.minutes_played,
            "screen_time_ratio": gp.screen_time_ratio,
            "stats": stats_dict,
            "score": gp.score.overall_score if gp.score else None,
            "score_confidence": gp.score.confidence if gp.score else None,
        })
    return result
