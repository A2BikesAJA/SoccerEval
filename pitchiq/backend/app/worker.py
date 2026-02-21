from __future__ import annotations

"""Celery worker for async video processing tasks."""

import logging
from collections import Counter
from celery import Celery
from datetime import datetime
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

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


def _update_progress(task, job, db, stage_name: str, progress: float):
    """Update both Celery state and the ProcessingJob record."""
    if job:
        job.current_stage = stage_name
        job.progress_pct = progress
        db.commit()
    task.update_state(
        state="PROGRESS",
        meta={"stage": stage_name, "progress": progress},
    )


@celery_app.task(bind=True, name="process_game_video")
def process_game_video(self, game_id: int):
    """Main video processing pipeline task.

    Stages:
    1. Transcode video
    2. Extract frames
    3. Detect players & ball
    4. Classify teams by jersey color
    5. Read jersey numbers (OCR)
    6. Track players across frames
    7. Compute statistics
    8. Calculate Player Scores
    9. Update PIQ Ratings
    """
    from app.models.base import SessionLocal
    from app.models.game import Game, GameStatus
    from app.models.game_player import GamePlayer
    from app.models.player import Player, POSITION_GROUP_MAP
    from app.models.processing import ProcessingJob
    from app.models.tracking import TrackingEvent
    from app.models.stats import PlayerGameStats, TeamGameStats
    from app.models.scores import PlayerScore

    db = SessionLocal()
    job = None
    try:
        # Get game and job
        game = db.query(Game).filter(Game.id == game_id).first()
        if not game:
            return {"error": f"Game {game_id} not found"}

        job = (
            db.query(ProcessingJob)
            .filter(ProcessingJob.game_id == game_id, ProcessingJob.status == "queued")
            .order_by(ProcessingJob.id.desc())
            .first()
        )
        if job:
            job.status = "running"
            job.started_at = datetime.utcnow()
            db.commit()

        game.status = GameStatus.PROCESSING
        db.commit()

        # Load game players for this game
        game_players = db.query(GamePlayer).filter(GamePlayer.game_id == game_id).all()

        # Determine age group for benchmarks
        age_group = game.age_group or "U14"

        # ---------------------------------------------------------------
        # Stage 1: Transcode video (10%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Transcoding video", 10)

        from app.services.video_processor import VideoProcessor
        vp = VideoProcessor()

        video_path = game.video_path
        processed_path = video_path  # fallback if transcode fails

        if video_path and Path(video_path).exists():
            try:
                video_info = vp.get_video_info(video_path)
                game.duration_minutes = video_info.duration_seconds / 60
                db.commit()

                processed_path = vp.transcode(video_path, game_id)
                logger.info("Game %d: Transcoded to %s (%.1f min)",
                            game_id, processed_path, game.duration_minutes or 0)
            except Exception as exc:
                logger.warning("Game %d: Transcode failed, using original: %s",
                               game_id, exc)
                try:
                    video_info = vp.get_video_info(video_path)
                    game.duration_minutes = video_info.duration_seconds / 60
                    db.commit()
                except Exception:
                    game.duration_minutes = 0
                    db.commit()
        else:
            logger.warning("Game %d: No video file at %s", game_id, video_path)
            game.duration_minutes = 0
            db.commit()

        game_duration = game.duration_minutes or 0

        # ---------------------------------------------------------------
        # Stage 2: Extract frames (20%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Extracting frames", 20)

        frame_paths = []
        if processed_path and Path(processed_path).exists():
            try:
                frame_paths = vp.extract_frames(processed_path, game_id)
                logger.info("Game %d: Extracted %d frames", game_id, len(frame_paths))
            except Exception as exc:
                logger.warning("Game %d: Frame extraction failed: %s", game_id, exc)

        # ---------------------------------------------------------------
        # Stage 3: Detect players & ball (40%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Detecting players and ball", 40)

        all_frame_detections = []  # list of list[Detection]
        ball_detections = []  # list of Optional[(x, y)]

        if frame_paths:
            try:
                from app.services.player_detector import PlayerDetector

                detector = PlayerDetector()

                for fp in frame_paths:
                    detections = detector.detect_players(fp)
                    all_frame_detections.append(detections)

                    ball_dets = [d for d in detections if d.class_label == "ball"]
                    if ball_dets:
                        best_ball = max(ball_dets, key=lambda d: d.confidence)
                        ball_detections.append(best_ball.center)
                    else:
                        ball_detections.append(None)

                logger.info("Game %d: Detection complete across %d frames",
                            game_id, len(frame_paths))
            except Exception as exc:
                logger.warning("Game %d: Detection stage failed: %s", game_id, exc)
                all_frame_detections = [[] for _ in frame_paths]
                ball_detections = [None for _ in frame_paths]

        # ---------------------------------------------------------------
        # Stage 4: Classify teams by jersey color (50%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Classifying teams by jersey color", 50)

        if frame_paths and all_frame_detections:
            try:
                import cv2
                from app.services.player_detector import PlayerDetector as PD4

                detector_for_classify = PD4()

                for fp, dets in zip(frame_paths, all_frame_detections):
                    if dets:
                        frame = cv2.imread(fp)
                        if frame is not None:
                            detector_for_classify.classify_teams(dets, frame)

                logger.info("Game %d: Team classification complete", game_id)
            except Exception as exc:
                logger.warning("Game %d: Team classification failed: %s", game_id, exc)

        # ---------------------------------------------------------------
        # Stage 5: Read jersey numbers (OCR) (60%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Reading jersey numbers", 60)

        jersey_readings = {}  # track_id -> list of (jersey_number, confidence)

        if frame_paths and all_frame_detections:
            try:
                import cv2
                from app.services.jersey_ocr import JerseyOCR

                ocr = JerseyOCR()

                for fp, dets in zip(frame_paths, all_frame_detections):
                    frame = cv2.imread(fp)
                    if frame is None:
                        continue

                    player_dets = [d for d in dets if d.class_label == "player"]
                    for det in player_dets:
                        number, conf = ocr.read_jersey_number(frame, det.bbox)
                        if number is not None:
                            track_key = det.track_id or id(det)
                            if track_key not in jersey_readings:
                                jersey_readings[track_key] = []
                            jersey_readings[track_key].append((number, conf))

                logger.info("Game %d: OCR complete, %d jersey sightings",
                            game_id, sum(len(v) for v in jersey_readings.values()))
            except Exception as exc:
                logger.warning("Game %d: OCR stage failed: %s", game_id, exc)

        # ---------------------------------------------------------------
        # Stage 6: Track players across frames (70%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Tracking players across frames", 70)

        tracker_results = {}  # frame_idx -> {track_id -> detection_dict}
        all_tracking_events = []  # list of dicts for stats engine

        if all_frame_detections:
            try:
                from app.services.player_tracker import PlayerTracker
                from app.services.ball_tracker import BallTracker
                from app.services.visibility_tracker import VisibilityTracker

                fps = settings.default_detection_fps
                if game_duration > 0 and frame_paths:
                    fps = len(frame_paths) / (game_duration * 60)
                    fps = max(fps, 0.5)

                player_tracker = PlayerTracker(fps=fps)
                ball_tracker_svc = BallTracker(fps=fps)
                vis_tracker = VisibilityTracker()

                for frame_idx, dets in enumerate(all_frame_detections):
                    player_dets = [d for d in dets if d.class_label in ("player", "referee")]

                    det_dicts = [{
                        "bbox": d.bbox,
                        "confidence": d.confidence,
                        "class_label": d.class_label,
                        "team": d.team,
                    } for d in player_dets]

                    assignments = player_tracker.update(det_dicts)
                    tracker_results[frame_idx] = assignments
                    vis_tracker.update(frame_idx, list(assignments.keys()), [])

                # Ball tracking
                ball_trajectory = ball_tracker_svc.track_ball(ball_detections)

                # Map tracks to game_players by jersey number
                track_to_player_id = {}

                for track_id in player_tracker.get_all_tracks():
                    track = player_tracker.get_track(track_id)
                    if track is None:
                        continue
                    readings = jersey_readings.get(track_id, [])
                    if readings:
                        number_counts = Counter(r[0] for r in readings)
                        best_number = number_counts.most_common(1)[0][0]

                        for gp in game_players:
                            player = db.query(Player).filter(Player.id == gp.player_id).first()
                            if player and player.jersey_number == best_number:
                                track_to_player_id[track_id] = player.id
                                break

                # Generate tracking events from position data
                timestamp_per_frame = (game_duration * 60) / max(len(all_frame_detections), 1)

                for frame_idx, assignments in tracker_results.items():
                    t = frame_idx * timestamp_per_frame

                    for track_id, det_dict in assignments.items():
                        player_id = track_to_player_id.get(track_id)
                        if player_id is None:
                            continue

                        bbox = det_dict["bbox"]
                        cx = (bbox[0] + bbox[2]) / 2.0
                        cy = (bbox[1] + bbox[3]) / 2.0

                        evt = {
                            "event_type": "position_sample",
                            "player_id": player_id,
                            "timestamp_seconds": t,
                            "x_position": cx,
                            "y_position": cy,
                            "metadata": {},
                        }
                        all_tracking_events.append(evt)

                        db.add(TrackingEvent(
                            game_id=game_id,
                            event_type="position_sample",
                            player_id=player_id,
                            timestamp_seconds=t,
                            x_position=cx,
                            y_position=cy,
                        ))

                # Ball possession events
                for i, bs in enumerate(ball_trajectory):
                    if bs.position and bs.possessing_player_id:
                        pid = track_to_player_id.get(bs.possessing_player_id)
                        if pid:
                            t = i * timestamp_per_frame
                            all_tracking_events.append({
                                "event_type": "touch",
                                "player_id": pid,
                                "timestamp_seconds": t,
                                "x_position": bs.position[0],
                                "y_position": bs.position[1],
                                "metadata": {},
                            })

                # Update visibility data on game_players
                for gp in game_players:
                    player_track_ids = [
                        tid for tid, pid in track_to_player_id.items()
                        if pid == gp.player_id
                    ]

                    if player_track_ids:
                        tid = player_track_ids[0]
                        track = player_tracker.get_track(tid)
                        if track:
                            gp.visible_frame_count = track.total_visible_frames
                            gp.total_game_frames = len(all_frame_detections)
                            if gp.total_game_frames > 0:
                                gp.screen_time_ratio = (
                                    track.total_visible_frames / gp.total_game_frames
                                )
                            gp.identity_confidence = 0.8

                            player = db.query(Player).filter(
                                Player.id == gp.player_id
                            ).first()
                            pos = player.position.value if player and player.position else None
                            gp.adjusted_screen_time_ratio = (
                                vis_tracker.get_adjusted_screen_time(tid, position=pos)
                            )
                    else:
                        gp.total_game_frames = len(all_frame_detections)

                db.commit()
                logger.info(
                    "Game %d: Tracking complete, %d events, %d players mapped",
                    game_id, len(all_tracking_events), len(track_to_player_id),
                )

            except Exception as exc:
                logger.warning("Game %d: Tracking stage failed: %s", game_id, exc)
                db.rollback()

        # ---------------------------------------------------------------
        # Stage 7: Compute statistics (80%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Computing player statistics", 80)

        all_player_stats = {}  # player_id -> stats dict

        try:
            from app.services.stats_engine import StatsEngine
            stats_engine = StatsEngine()

            for gp in game_players:
                player_events = [
                    e for e in all_tracking_events
                    if e.get("player_id") == gp.player_id
                ]

                player_stats = stats_engine.compute_player_stats(
                    tracking_events=player_events,
                    player_id=gp.player_id,
                    game_duration=game_duration,
                )

                all_player_stats[gp.player_id] = player_stats

                # Estimate minutes played from screen time
                gp.minutes_played = game_duration * max(gp.screen_time_ratio, 0.5)

                # Store individual stats
                data_density = gp.screen_time_ratio if gp.screen_time_ratio > 0 else 0.5
                is_extrapolated = data_density < settings.min_screen_time_for_extrapolation

                for metric_name, metric_value in player_stats.items():
                    db.add(PlayerGameStats(
                        game_player_id=gp.id,
                        metric_name=metric_name,
                        metric_value=metric_value,
                        data_density=data_density,
                        is_extrapolated=is_extrapolated,
                    ))

            # Compute team stats
            game_data = {
                "score_home": game.score_home or 0,
                "score_away": game.score_away or 0,
                "duration_minutes": game_duration,
            }
            team_stats = stats_engine.compute_team_stats(all_player_stats, game_data)

            for metric_name, metric_value in team_stats.items():
                db.add(TeamGameStats(
                    game_id=game_id,
                    metric_name=metric_name,
                    metric_value=metric_value,
                ))

            db.commit()
            logger.info("Game %d: Stats computed for %d players",
                        game_id, len(all_player_stats))

        except Exception as exc:
            logger.warning("Game %d: Stats computation failed: %s", game_id, exc)
            db.rollback()

        # ---------------------------------------------------------------
        # Stage 8: Calculate Player Scores (90%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Calculating Player Scores", 90)

        try:
            from app.services.score_calculator import ScoreCalculator
            score_calc = ScoreCalculator()

            for gp in game_players:
                player_stats = all_player_stats.get(gp.player_id, {})
                if not player_stats:
                    continue

                player = db.query(Player).filter(Player.id == gp.player_id).first()
                position_group = POSITION_GROUP_MAP.get(
                    player.position.value if player and player.position else "CM",
                    "CM",
                )

                score_result = score_calc.calculate_player_score(
                    player_stats=player_stats,
                    position_group=position_group,
                    age_group=age_group,
                    minutes_played=gp.minutes_played or 0,
                    game_duration=game_duration,
                )

                db.add(PlayerScore(
                    game_player_id=gp.id,
                    overall_score=score_result.overall_score,
                    confidence=score_result.confidence,
                    category_scores=score_result.category_scores,
                    bonus_events=score_result.bonus_events,
                    raw_composite=score_result.raw_composite,
                    minutes_adjustment=score_result.minutes_adjustment,
                ))

            db.commit()
            logger.info("Game %d: Player scores calculated", game_id)

        except Exception as exc:
            logger.warning("Game %d: Score calculation failed: %s", game_id, exc)
            db.rollback()

        # ---------------------------------------------------------------
        # Stage 9: Update PIQ Ratings (95%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Updating PIQ Ratings", 95)

        try:
            from app.services.piq_rating_engine import PIQRatingEngine
            piq_engine = PIQRatingEngine()

            for gp in game_players:
                player_stats = all_player_stats.get(gp.player_id, {})
                if not player_stats:
                    continue

                piq_engine.update_piq_rating(
                    player_id=gp.player_id,
                    new_game_stats=player_stats,
                    db_session=db,
                )

            db.commit()
            logger.info("Game %d: PIQ ratings updated", game_id)

        except Exception as exc:
            logger.warning("Game %d: PIQ rating update failed: %s", game_id, exc)
            db.rollback()

        # ---------------------------------------------------------------
        # Finalize (100%)
        # ---------------------------------------------------------------
        _update_progress(self, job, db, "Finalizing results", 100)

        game.status = GameStatus.COMPLETED
        if job:
            job.status = "completed"
            job.progress_pct = 100
            job.completed_at = datetime.utcnow()
            job.current_stage = "Complete"
        db.commit()

        logger.info("Game %d: Processing complete", game_id)
        return {"status": "completed", "game_id": game_id}

    except Exception as e:
        logger.exception("Game %d: Processing failed", game_id)
        try:
            game = db.query(Game).filter(Game.id == game_id).first()
            if game:
                game.status = GameStatus.ERROR
            if job:
                job.status = "failed"
                job.error_message = str(e)[:1000]
                job.completed_at = datetime.utcnow()
            db.commit()
        except Exception:
            db.rollback()
        raise

    finally:
        db.close()
