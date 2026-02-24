from __future__ import annotations

"""Club API routes."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.models.club import Club
from app.schemas.club import ClubCreate, ClubResponse

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/", response_model=list[ClubResponse])
def list_clubs(db: Session = Depends(get_db)):
    return db.query(Club).all()


@router.post("/", status_code=201)
def create_club(club: ClubCreate, db: Session = Depends(get_db)):
    try:
        db_club = Club(name=club.name, logo_url=club.logo_url)
        db.add(db_club)
        db.commit()
        db.refresh(db_club)
        result = ClubResponse.model_validate(db_club)
        return JSONResponse(status_code=201, content=result.model_dump(mode="json"))
    except Exception as exc:
        db.rollback()
        logger.exception("Failed to create club")
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{club_id}", response_model=ClubResponse)
def get_club(club_id: int, db: Session = Depends(get_db)):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    return club


@router.delete("/{club_id}", status_code=204)
def delete_club(club_id: int, db: Session = Depends(get_db)):
    club = db.query(Club).filter(Club.id == club_id).first()
    if not club:
        raise HTTPException(status_code=404, detail="Club not found")
    db.delete(club)
    db.commit()
