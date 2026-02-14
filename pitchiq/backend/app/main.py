from __future__ import annotations

"""PitchIQ — Youth Soccer Analytics Platform API."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.models.base import Base, engine, SessionLocal
from app.models.club import Club
from app.models.team import Team, AgeGroup
from app.routers import clubs, teams, players, games, stats, piq, processing

# Create database tables
Base.metadata.create_all(bind=engine)

# Seed demo data if empty
def _seed_demo_data():
    db = SessionLocal()
    try:
        if db.query(Club).count() == 0:
            club = Club(id=1, name="FC Warriors", logo_url=None)
            db.add(club)
            db.flush()
            db.add(Team(id=1, club_id=1, name="FC Warriors U14 Boys", age_group=AgeGroup.U14, competition_tier=6))
            db.add(Team(id=2, club_id=1, name="FC Warriors U12 Girls", age_group=AgeGroup.U12, competition_tier=6))
            db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

_seed_demo_data()

app = FastAPI(
    title=settings.app_name,
    description="AI-powered youth soccer game footage analytics platform",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directories exist
for dir_path in [settings.upload_dir, settings.processed_dir, settings.frames_dir]:
    Path(dir_path).mkdir(parents=True, exist_ok=True)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory=str(settings.upload_dir)), name="uploads")

# Include routers
prefix = settings.api_prefix
app.include_router(clubs.router, prefix=f"{prefix}/clubs", tags=["clubs"])
app.include_router(teams.router, prefix=f"{prefix}/teams", tags=["teams"])
app.include_router(players.router, prefix=f"{prefix}/players", tags=["players"])
app.include_router(games.router, prefix=f"{prefix}/games", tags=["games"])
app.include_router(stats.router, prefix=f"{prefix}/stats", tags=["stats"])
app.include_router(piq.router, prefix=f"{prefix}/piq", tags=["piq"])
app.include_router(processing.router, prefix=f"{prefix}/processing", tags=["processing"])


@app.get("/")
async def root():
    return {
        "name": settings.app_name,
        "version": "1.0.0",
        "description": "Youth Soccer Analytics Platform",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
