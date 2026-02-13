"""Celery worker for async video processing tasks."""

from celery import Celery
from datetime import datetime

from app.config import settings

celery_app = Celery(
    "pitchiq",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
)


@celery_app.task(bind=True, name="process_game_video")
def process_game_video(self, game_id: int):
    """Main video processing pipeline task.

    Stages:
    1. Transcode video
    2. Extract frames
    3. Detect players & ball
    4. Classify teams
    5. Read jersey numbers (OCR)
    6. Track players across frames
    7. Compute statistics
    8. Calculate Player Scores
    9. Update PIQ Ratings
    """
    from app.models.base import SessionLocal
    from app.models.game import Game, GameStatus
    from app.models.processing import ProcessingJob

    db = SessionLocal()
    try:
        # Get game and job
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            return {"error": f"Game {game_id} not found"}

        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.game_id == game_id, ProcessingJob.status == "queued")
            .first()
        )
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

        game.status = GameStatus.PROCESSING
        db.commit()

        stages = [
            ("Transcoding video", 10),
            ("Extracting frames", 20),
            ("Detecting players and ball", 40),
            ("Classifying teams by jersey color", 50),
            ("Reading jersey numbers", 60),
            ("Tracking players across frames", 70),
            ("Computing player statistics", 80),
            ("Calculating Player Scores", 90),
            ("Updating PIQ Ratings", 95),
            ("Finalizing results", 100),
        ]

        for stage_name, progress in stages:
            if job:
                job.current_stage = stage_name
                job.progress_pct = progress
                db.commit()

            self.update_state(
                state="PROGRESS",
                meta={"stage": stage_name, "progress": progress},
            )

            # Stage 1: Transcode
            if progress == 10:
                from app.services.video_processor import VideoProcessor
                vp = VideoProcessor()
                if game.video_path:
                    video_info = vp.get_video_info(game.video_path)
                    game.duration_minutes = video_info.duration_seconds / 60

            # Stage 2: Extract frames
            elif progress == 20:
                pass  # Frame extraction handled by VideoProcessor

            # Stage 3-6: Detection, Classification, OCR, Tracking
            # In production, these stages would invoke the full CV pipeline:
            # - PlayerDetector for detection
            # - JerseyOCR for number reading
            # - PlayerTracker for multi-object tracking
            # - BallTracker for ball tracking & possession

            # Stage 7: Compute stats
            elif progress == 80:
                pass  # StatsEngine.compute_player_stats()

            # Stage 8: Calculate scores
            elif progress == 90:
                pass  # ScoreCalculator.calculate_player_score()

            # Stage 9: Update PIQ
            elif progress == 95:
                pass  # PIQRatingEngine.update_piq_rating()

        # Mark complete
        game.status = GameStatus.COMPLETED
        if job:
            job.status = "completed"
            job.progress_pct = 100
            job.completed_at = datetime.utcnow()
            job.current_stage = "Complete"
        db.commit()

        return {"status": "completed", "game_id": game_id}

    except Exception as e:
        game.status = GameStatus.ERROR
        if job:
            job.status = "failed"
            job.error_message = str(e)[:1000]
            job.completed_at = datetime.utcnow()
        db.commit()
        raise

    finally:
        db.close()
