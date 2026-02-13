"""Player Score (0-10) calculator for PitchIQ.

Computes a single-game performance score on a 0-10 scale by:
  1. Converting raw metrics to Z-scores against age-group benchmarks
  2. Mapping Z-scores to percentiles
  3. Weighting by position-specific category weights
  4. Applying minute adjustments and bonus events
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
from scipy import stats as scipy_stats

from app.config import settings
from app.services.stats_engine import (
    AGE_GROUP_BENCHMARKS,
    CATEGORY_METRIC_MAP,
    METRIC_DEFINITIONS,
    POSITION_WEIGHTS,
    StatsEngine,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Inverse metrics -- higher raw values are *worse* performance
# ---------------------------------------------------------------------------

INVERSE_METRICS: list[str] = [
    "turnovers",
    "dispossessions",
    "fouls_committed",
    "yellow_cards",
    "red_cards",
    "offsides",
    "goals_conceded",
    "goals_against_avg",
    "aerial_duels_lost",
    "own_goals",
]

# ---------------------------------------------------------------------------
# Bonus / penalty events applied on top of the composite score
# ---------------------------------------------------------------------------

BONUS_EVENTS: dict[str, float] = {
    "goal": 0.3,
    "assist": 0.2,
    "clean_sheet": 0.2,
    "penalty_save": 0.3,
    "red_card": -1.5,
    "yellow_card": -0.3,
    "own_goal": -0.5,
}

# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class PlayerScoreResult:
    """Container for the output of score calculation."""

    overall_score: float
    raw_composite: float
    confidence: float
    minutes_adjustment: float
    category_scores: dict[str, float] = field(default_factory=dict)
    bonus_events: dict[str, float] = field(default_factory=dict)
    metric_percentiles: dict[str, float] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# ScoreCalculator
# ---------------------------------------------------------------------------


class ScoreCalculator:
    """Calculate a single-game Player Score on a 0-10 scale."""

    def __init__(self) -> None:
        self._stats_engine = StatsEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def calculate_player_score(
        self,
        player_stats: dict[str, float],
        position_group: str,
        age_group: str,
        minutes_played: float,
        game_duration: float,
    ) -> PlayerScoreResult:
        """Run the full scoring pipeline for a player's single-game stats.

        Parameters
        ----------
        player_stats:
            Dict of metric_name -> raw value (output of
            ``StatsEngine.compute_player_stats``).
        position_group:
            One of GK, CB, FB, CDM, CM, CAM, W, ST.
        age_group:
            E.g. ``"U14"``.
        minutes_played:
            How many minutes the player was on the pitch.
        game_duration:
            Total game duration in minutes.

        Returns
        -------
        PlayerScoreResult with the final 0-10 score and breakdown.
        """

        # Step 1 & 2: Z-score normalisation -> percentile
        benchmarks = self._stats_engine.get_benchmarks(age_group)
        metric_percentiles = self._compute_percentiles(
            player_stats, benchmarks,
        )

        # Step 3: Group metrics into categories per position weight table
        category_metrics = self._stats_engine.categorize_metrics(
            player_stats, position_group,
        )

        # Step 4-6: Category scores (average percentile within category)
        category_scores = self._compute_category_scores(
            metric_percentiles, category_metrics,
        )

        # Step 7-8: Weighted sum using position weights
        raw_composite = self._compute_weighted_composite(
            category_scores, position_group,
        )

        # Step 9: Scale 0-100 -> 0-10
        score = raw_composite / 10.0

        # Step 10: Minutes adjustment
        expected_half = game_duration / 2.0 if game_duration > 0 else 30.0
        confidence = min(1.0, minutes_played / expected_half) if expected_half > 0 else 1.0

        # Adjust: pull toward 5.0 (league average) if low confidence
        score = 5.0 + (score - 5.0) * confidence

        # Step 11: Bonus events
        applied_bonuses: dict[str, float] = {}
        bonus_total = 0.0

        goals = int(player_stats.get("goals", 0))
        if goals > 0:
            bonus = goals * BONUS_EVENTS["goal"]
            applied_bonuses["goal"] = bonus
            bonus_total += bonus

        assists = int(player_stats.get("assists", 0))
        if assists > 0:
            bonus = assists * BONUS_EVENTS["assist"]
            applied_bonuses["assist"] = bonus
            bonus_total += bonus

        if player_stats.get("clean_sheet", 0) >= 1.0 and position_group in {"GK", "CB", "FB", "CDM"}:
            bonus = BONUS_EVENTS["clean_sheet"]
            applied_bonuses["clean_sheet"] = bonus
            bonus_total += bonus

        penalty_saves = int(player_stats.get("penalty_saves", 0))
        if penalty_saves > 0:
            bonus = penalty_saves * BONUS_EVENTS["penalty_save"]
            applied_bonuses["penalty_save"] = bonus
            bonus_total += bonus

        red_cards = int(player_stats.get("red_cards", 0))
        if red_cards > 0:
            penalty = red_cards * BONUS_EVENTS["red_card"]
            applied_bonuses["red_card"] = penalty
            bonus_total += penalty

        yellow_cards = int(player_stats.get("yellow_cards", 0))
        if yellow_cards > 0:
            penalty = yellow_cards * BONUS_EVENTS["yellow_card"]
            applied_bonuses["yellow_card"] = penalty
            bonus_total += penalty

        own_goals = int(player_stats.get("own_goals", 0))
        if own_goals > 0:
            penalty = own_goals * BONUS_EVENTS["own_goal"]
            applied_bonuses["own_goal"] = penalty
            bonus_total += penalty

        score += bonus_total

        # Step 12: Cap at [0.0, 10.0]
        score = max(0.0, min(10.0, score))

        return PlayerScoreResult(
            overall_score=round(score, 2),
            raw_composite=round(raw_composite, 2),
            confidence=round(confidence, 3),
            minutes_adjustment=round(confidence, 3),
            category_scores={k: round(v, 2) for k, v in category_scores.items()},
            bonus_events=applied_bonuses,
            metric_percentiles={k: round(v, 2) for k, v in metric_percentiles.items()},
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_percentiles(
        player_stats: dict[str, float],
        benchmarks: dict[str, dict[str, float]],
    ) -> dict[str, float]:
        """Convert raw stat values to percentiles via Z-scores.

        Steps 1-4 of the pipeline:
          1. Compute Z = (value - mean) / std
          2. Convert Z to percentile using the normal CDF
          3. For inverse metrics, flip: percentile = 100 - percentile
        """
        percentiles: dict[str, float] = {}

        for metric, value in player_stats.items():
            bench = benchmarks.get(metric)
            if bench is None:
                # No benchmark data -- assume 50th percentile
                percentiles[metric] = 50.0
                continue

            mean = bench["mean"]
            std = bench["std"]
            if std <= 0:
                std = 1.0  # avoid division by zero

            # Step 1: Z-score
            z = (value - mean) / std

            # Step 2: CDF -> percentile [0, 100]
            percentile = float(scipy_stats.norm.cdf(z) * 100.0)

            # Step 3 (inverse): flip percentile for metrics where lower is better
            if metric in INVERSE_METRICS:
                percentile = 100.0 - percentile

            # Clamp to [0.5, 99.5] to avoid extremes
            percentile = max(0.5, min(99.5, percentile))

            percentiles[metric] = percentile

        return percentiles

    @staticmethod
    def _compute_category_scores(
        metric_percentiles: dict[str, float],
        category_metrics: dict[str, list[str]],
    ) -> dict[str, float]:
        """Compute the average percentile for each scoring category.

        Step 5-6 of the pipeline.
        """
        category_scores: dict[str, float] = {}

        for category, metrics in category_metrics.items():
            values = [metric_percentiles[m] for m in metrics if m in metric_percentiles]
            if values:
                category_scores[category] = float(np.mean(values))
            else:
                category_scores[category] = 50.0  # neutral fallback

        return category_scores

    @staticmethod
    def _compute_weighted_composite(
        category_scores: dict[str, float],
        position_group: str,
    ) -> float:
        """Multiply each category by its position weight and sum.

        Steps 7-8.  Result is on a 0-100 scale.
        """
        weights = POSITION_WEIGHTS.get(position_group, POSITION_WEIGHTS["CM"])

        weighted_sum = 0.0
        total_weight = 0.0

        for category, weight in weights.items():
            score = category_scores.get(category, 50.0)
            weighted_sum += score * weight
            total_weight += weight

        if total_weight > 0:
            return weighted_sum / total_weight  # normalise in case weights don't sum to 1
        return 50.0
