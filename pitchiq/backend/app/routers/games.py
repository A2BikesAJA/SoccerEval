from __future__ import annotations

"""Game API routes — upload, management, and video processing."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from pathlib import Path
from datetime import date as date_type
import shutil
import uuid
import json

from app.models.base import get_db
from app.models.game import Game, GameVideoSource, GameStatus, CameraSourceType
from app.models.game_player import GamePlayer
from app.models.player import Player
from app.models.team import Team
from app.models.processing import ProcessingJob
from app.schemas.game import GameCreate, GameResponse, GameDetailResponse
from app.config import settings

router = APIRouter()

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
MAX_SIZE_BYTES = settings.max_upload_size_mb * 1024 * 1024


@router.get("/", response_model=list[GameResponse])
def list_games(team_id: int | None = None, db: Session = Depends(get_db)):
    query = db.query(Game).order_by(Game.game_date.desc())
    if team_id:
        query = query.filter(Game.team_id == team_id)
    return query.all()


@router.get("/{game_id}", response_model=GameDetailResponse)
def get_game(game_id: int, db: Session = Depends(get_db)):
    game = (
        db.query(Game)
        .options(
            joinedload(Game.video_sources),
            joinedload(Game.game_players).joinedload(GamePlayer.player),
            joinedload(Game.game_players).joinedload(GamePlayer.score),
            joinedload(Game.team_stats),
        )
        .filter(Game.id == game_id)
        .first()
    )
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return game


@router.post("/upload", response_model=GameResponse, status_code=201)
async def upload_game(
    video: UploadFile = File(...),
    team_id: int = Form(...),
    opponent_name: str = Form(...),
    game_date: str = Form(...),
    age_group: str = Form(None),
    formation: str = Form(None),
    camera_source_type: str = Form("other"),
    roster_json: str = Form(None),
    db: Session = Depends(get_db),
):
    """Upload a game video with metadata."""
    # Validate team exists
    team = db.query(Team).filter(Team.id == team_id).first()
    if not team:
        raise HTTPException(status_code=400, detail=f"Team with id {team_id} not found")

    # Validate file extension
    ext = Path(video.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Resolve camera source enum (fall back to OTHER)
    try:
        cam_enum = CameraSourceType(camera_source_type)
    except ValueError:
        cam_enum = CameraSourceType.OTHER

    # Generate unique filename and save
    file_id = uuid.uuid4().hex
    filename = f"{file_id}{ext}"
    upload_path = Path(settings.upload_dir) / filename

    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    # Create game record
    game = Game(
        team_id=team_id,
        opponent_name=opponent_name,
        game_date=date_type.fromisoformat(game_date),
        age_group=age_group,
        formation=formation,
        video_path=str(upload_path),
        status=GameStatus.PENDING,
    )
    db.add(game)
    db.flush()

    # Create video source record
    source = GameVideoSource(
        game_id=game.id,
        source_type=cam_enum,
        video_path=str(upload_path),
        is_primary=True,
    )
    db.add(source)

    # Process roster if provided
    if roster_json:
        roster = json.loads(roster_json)
        for entry in roster:
            jersey_num = entry.get("jersey_number")
            name = entry.get("name", "Unknown")
            position = entry.get("position")

            # Find or create player
            player = db.query(Player).filter(
                Player.team_id == team_id,
                Player.jersey_number == jersey_num,
            ).first()
            if not player:
                player = Player(
                    team_id=team_id,
                    name=name,
                    jersey_number=jersey_num,
                    position=position,
                )
                db.add(player)
                db.flush()

            # Create game player entry
            game_player = GamePlayer(
                game_id=game.id,
                player_id=player.id,
                position_played=position,
                started=True,
            )
            db.add(game_player)

    # Create processing job
    job = ProcessingJob(game_id=game.id, status="queued")
    db.add(job)

    db.commit()
    db.refresh(game)

    # TODO: Trigger Celery task for video processing
    # process_game_video.delay(game.id)

    return game


@router.post("/{game_id}/secondary-video", status_code=201)
async def upload_secondary_video(
    game_id: int,
    video: UploadFile = File(...),
    source_type: str = Form("sideline"),
    temporal_offset_ms: int = Form(0),
    db: Session = Depends(get_db),
):
    """Upload a secondary video source for multi-source fusion."""
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    ext = Path(video.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Invalid file type")

    file_id = uuid.uuid4().hex
    filename = f"{file_id}_secondary{ext}"
    upload_path = Path(settings.upload_dir) / filename

    with open(upload_path, "wb") as buffer:
        shutil.copyfileobj(video.file, buffer)

    source = GameVideoSource(
        game_id=game_id,
        source_type=source_type,
        video_path=str(upload_path),
        is_primary=False,
        temporal_offset_ms=temporal_offset_ms,
    )
    db.add(source)
    db.commit()

    return {"message": "Secondary video uploaded", "source_id": source.id}


@router.delete("/{game_id}", status_code=204)
def delete_game(game_id: int, db: Session = Depends(get_db)):
    game = db.query(Game).filter(Game.id == game_id).first()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    db.delete(game)
    db.commit()
