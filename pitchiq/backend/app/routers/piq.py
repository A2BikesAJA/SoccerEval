"""PIQ Rating API routes — persistent player ratings and scouting."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload

from app.models.base import get_db
from app.models.player import Player
from app.models.team import Team
from app.models.scores import PIQRating, PIQRatingHistory
from app.schemas.stats import PIQRatingResponse, PIQRatingHistoryResponse

router = APIRouter()


@router.get("/player/{player_id}", response_model=PIQRatingResponse)
def get_player_piq(player_id: int, db: Session = Depends(get_db)):
    """Get the current PIQ Rating for a player."""
    rating = (
        db.query(PIQRating)
        .filter(PIQRating.player_id == player_id)
        .order_by(PIQRating.id.desc())
        .first()
    )
    if not rating:
        raise HTTPException(status_code=404, detail="PIQ Rating not found for this player")
    return rating


@router.get("/player/{player_id}/history", response_model=list[PIQRatingHistoryResponse])
def get_player_piq_history(player_id: int, db: Session = Depends(get_db)):
    """Get PIQ Rating history for trend tracking."""
    history = (
        db.query(PIQRatingHistory)
        .filter(PIQRatingHistory.player_id == player_id)
        .order_by(PIQRatingHistory.snapshot_date.asc())
        .all()
    )
    return history


@router.get("/scouting")
def scouting_search(
    age_group: str | None = None,
    position: str | None = None,
    min_ovr: int = Query(default=1, ge=1, le=99),
    max_ovr: int = Query(default=99, ge=1, le=99),
    competition_tier: int | None = Query(default=None, ge=1, le=8),
    sort_by: str = "ovr",
    limit: int = Query(default=50, le=200),
    db: Session = Depends(get_db),
):
    """Search and filter players across all clubs for scouting."""
    query = (
        db.query(PIQRating)
        .join(Player, PIQRating.player_id == Player.id)
        .join(Team, Player.team_id == Team.id)
        .filter(PIQRating.ovr >= min_ovr, PIQRating.ovr <= max_ovr)
    )

    if age_group:
        query = query.filter(Team.age_group == age_group)
    if position:
        query = query.filter(Player.position == position)
    if competition_tier:
        query = query.filter(Team.competition_tier == competition_tier)

    # Sort
    sort_map = {
        "ovr": PIQRating.ovr.desc(),
        "spd": PIQRating.spd.desc(),
        "sht": PIQRating.sht.desc(),
        "pas": PIQRating.pas.desc(),
        "drb": PIQRating.drb.desc(),
        "def": PIQRating._def.desc(),
        "phy": PIQRating.phy.desc(),
    }
    order = sort_map.get(sort_by, PIQRating.ovr.desc())
    query = query.order_by(order).limit(limit)

    ratings = query.all()
    result = []
    for rating in ratings:
        player = db.query(Player).filter(Player.id == rating.player_id).first()
        team = db.query(Team).filter(Team.id == player.team_id).first() if player else None
        result.append({
            "player_id": rating.player_id,
            "player_name": player.name if player else "Unknown",
            "jersey_number": player.jersey_number if player else None,
            "position": player.position if player else None,
            "team_name": team.name if team else None,
            "age_group": team.age_group if team else None,
            "competition_tier": team.competition_tier if team else None,
            "ovr": rating.ovr,
            "spd": rating.spd,
            "sht": rating.sht,
            "pas": rating.pas,
            "drb": rating.drb,
            "def_": rating._def,
            "phy": rating.phy,
            "games_analyzed": rating.games_analyzed_count,
            "confidence_level": rating.confidence_level,
        })
    return result


@router.get("/what-if/{player_id}")
def what_if_tier(
    player_id: int,
    target_tier: int = Query(ge=1, le=8),
    db: Session = Depends(get_db),
):
    """Simulate what a player's PIQ Rating would be at a different competition tier."""
    from app.services.competition_tier import CompetitionTierService

    rating = (
        db.query(PIQRating)
        .filter(PIQRating.player_id == player_id)
        .order_by(PIQRating.id.desc())
        .first()
    )
    if not rating:
        raise HTTPException(status_code=404, detail="PIQ Rating not found")

    tier_service = CompetitionTierService()
    current_tier = rating.competition_tier or 6
    simulated = tier_service.simulate_tier_change(
        current_ovr=rating.ovr,
        current_tier=current_tier,
        target_tier=target_tier,
        attributes={
            "spd": rating.spd, "sht": rating.sht, "pas": rating.pas,
            "drb": rating.drb, "def_": rating._def, "phy": rating.phy,
        }
    )
    return {
        "player_id": player_id,
        "current_tier": current_tier,
        "target_tier": target_tier,
        "current_ovr": rating.ovr,
        "estimated_ovr": simulated["ovr"],
        "estimated_attributes": simulated["attributes"],
        "tier_name": tier_service.get_tier_name(target_tier),
    }


@router.get("/compare")
def compare_players(
    player_ids: str = Query(..., description="Comma-separated player IDs"),
    db: Session = Depends(get_db),
):
    """Compare PIQ Ratings of multiple players side by side."""
    ids = [int(x.strip()) for x in player_ids.split(",")]
    if len(ids) < 2 or len(ids) > 4:
        raise HTTPException(status_code=400, detail="Provide 2-4 player IDs")

    result = []
    for pid in ids:
        rating = (
            db.query(PIQRating)
            .filter(PIQRating.player_id == pid)
            .order_by(PIQRating.id.desc())
            .first()
        )
        player = db.query(Player).filter(Player.id == pid).first()
        team = db.query(Team).filter(Team.id == player.team_id).first() if player else None

        result.append({
            "player_id": pid,
            "player_name": player.name if player else "Unknown",
            "position": player.position if player else None,
            "team_name": team.name if team else None,
            "age_group": team.age_group if team else None,
            "competition_tier": team.competition_tier if team else None,
            "rating": {
                "ovr": rating.ovr if rating else None,
                "spd": rating.spd if rating else None,
                "sht": rating.sht if rating else None,
                "pas": rating.pas if rating else None,
                "drb": rating.drb if rating else None,
                "def_": rating._def if rating else None,
                "phy": rating.phy if rating else None,
                "sub_attributes": rating.sub_attributes if rating else None,
                "games_analyzed": rating.games_analyzed_count if rating else 0,
                "confidence_level": rating.confidence_level if rating else "calculating",
            }
        })
    return result
