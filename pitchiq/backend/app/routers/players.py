from __future__ import annotations

"""Player API routes."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
import csv
import io

from app.models.base import get_db
from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerResponse, RosterEntry

router = APIRouter()


@router.get("/", response_model=list[PlayerResponse])
def list_players(team_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Player)
    if team_id:
        query = query.filter(Player.team_id == team_id)
    return query.all()


@router.post("/", response_model=PlayerResponse, status_code=201)
def create_player(player: PlayerCreate, db: Session = Depends(get_db)):
    db_player = Player(**player.model_dump())
    db.add(db_player)
    db.commit()
    db.refresh(db_player)
    return db_player


@router.get("/{player_id}", response_model=PlayerResponse)
def get_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.put("/{player_id}", response_model=PlayerResponse)
def update_player(player_id: int, player_data: PlayerCreate, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    for key, value in player_data.model_dump().items():
        setattr(player, key, value)
    db.commit()
    db.refresh(player)
    return player


@router.post("/roster/{team_id}", response_model=list[PlayerResponse])
def import_roster(team_id: int, roster: list[RosterEntry], db: Session = Depends(get_db)):
    """Import a full roster (jersey number -> player name mapping)."""
    players = []
    for entry in roster:
        existing = db.query(Player).filter(
            Player.team_id == team_id,
            Player.jersey_number == entry.jersey_number
        ).first()
        if existing:
            existing.name = entry.name
            if entry.position:
                existing.position = entry.position
            players.append(existing)
        else:
            player = Player(
                team_id=team_id,
                name=entry.name,
                jersey_number=entry.jersey_number,
                position=entry.position,
            )
            db.add(player)
            players.append(player)
    db.commit()
    for p in players:
        db.refresh(p)
    return players


@router.post("/roster/{team_id}/csv", response_model=list[PlayerResponse])
async def import_roster_csv(team_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    """Import roster from CSV file (columns: jersey_number, name, position)."""
    content = await file.read()
    reader = csv.DictReader(io.StringIO(content.decode("utf-8")))
    players = []
    for row in reader:
        jersey_number = int(row.get("jersey_number", row.get("number", 0)))
        name = row.get("name", row.get("player_name", "Unknown"))
        position = row.get("position", None)
        existing = db.query(Player).filter(
            Player.team_id == team_id,
            Player.jersey_number == jersey_number
        ).first()
        if existing:
            existing.name = name
            if position:
                existing.position = position
            players.append(existing)
        else:
            player = Player(
                team_id=team_id,
                name=name,
                jersey_number=jersey_number,
                position=position,
            )
            db.add(player)
            players.append(player)
    db.commit()
    for p in players:
        db.refresh(p)
    return players


@router.delete("/{player_id}", status_code=204)
def delete_player(player_id: int, db: Session = Depends(get_db)):
    player = db.query(Player).filter(Player.id == player_id).first()
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    db.delete(player)
    db.commit()
