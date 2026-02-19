from __future__ import annotations

"""PitchIQ — Youth Soccer Analytics Platform API."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import ResponseValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.config import settings
from app.models.base import Base, engine
from app.routers import clubs, teams, players, games, stats, piq, processing

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create database tables
Base.metadata.create_all(bind=engine)

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


@app.exception_handler(ResponseValidationError)
async def response_validation_handler(request: Request, exc: ResponseValidationError):
    logger.error("Response validation error on %s: %s", request.url, exc.errors())
    return JSONResponse(status_code=500, content={"detail": str(exc.errors())})


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
