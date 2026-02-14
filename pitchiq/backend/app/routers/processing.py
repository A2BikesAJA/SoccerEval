from __future__ import annotations

"""Processing job API routes."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.base import get_db
from app.models.processing import ProcessingJob
from app.schemas.processing import ProcessingJobResponse

router = APIRouter()


@router.get("/game/{game_id}", response_model=list[ProcessingJobResponse])
def get_game_processing_status(game_id: int, db: Session = Depends(get_db)):
    """Get processing job status for a game."""
    jobs = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.game_id == game_id)
        .order_by(ProcessingJob.id.desc())
        .all()
    )
    return jobs


@router.get("/{job_id}", response_model=ProcessingJobResponse)
def get_job_status(job_id: int, db: Session = Depends(get_db)):
    """Get a specific processing job's status."""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Processing job not found")
    return job


@router.post("/game/{game_id}/retry", response_model=ProcessingJobResponse)
def retry_processing(game_id: int, db: Session = Depends(get_db)):
    """Retry a failed processing job."""
    # Cancel any existing running jobs
    existing = (
        db.query(ProcessingJob)
        .filter(ProcessingJob.game_id == game_id, ProcessingJob.status.in_(["queued", "running"]))
        .all()
    )
    for job in existing:
        job.status = "cancelled"

    # Create new job
    new_job = ProcessingJob(game_id=game_id, status="queued")
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # TODO: Trigger Celery task
    # process_game_video.delay(game_id)

    return new_job
