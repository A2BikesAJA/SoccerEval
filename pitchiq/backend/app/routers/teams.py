from __future__ import annotations

"""Team API routes."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.models.team import Team
from app.schemas.team import TeamCreate, TeamResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=list[TeamResponse])
def list_teams(club_id: Optional[int] = None, db: Session = Depends(get_db)):
    query = db.query(Team)
    if club_id:
        query = query.filter(Team.club_id == club_id)
    return query.all()


@router.post("/", status_code=201)
def create_team(team: TeamCreate, db: Session = Depends(get_db)):
    try:
        db_team = Team(**team.model_dump())
        db.add(db_team)
        db.commit()
        db.refresh(db_team)
        result = TeamResponse.model_validate(db_team)
        return JSONResponse(status_code=201, content=result.model_dump(mode="json"))
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create team")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{team_id}", response_model=TeamResponse)
def get_team(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    return team


@router.put("/{team_id}", response_model=TeamResponse)
def update_team(team_id: int, team_data: TeamCreate, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    for key, value in team_data.model_dump().items():
        setattr(team, key, value)
    db.commit()
    db.refresh(team)
    return team


@router.delete("/{team_id}", status_code=204)
def delete_team(team_id: int, db: Session = Depends(get_db)):
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")
    db.delete(team)
    db.commit()
