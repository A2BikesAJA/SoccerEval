"""Statistics computation engine for PitchIQ.

Computes all player and team statistics from tracking data, categorizes
metrics by position group, and provides age-group benchmark data for
normalization.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Any, Optional

import numpy as np

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Position-specific metric weight tables
# ---------------------------------------------------------------------------

POSITION_WEIGHTS: dict[str, dict[str, float]] = {
    "GK": {
        "saves": 0.20, "save_percentage": 0.15, "goals_conceded": 0.15,
        "goals_against_avg": 0.10, "clean_sheet": 0.05, "catches": 0.05,
        "punches": 0.03, "distribution_accuracy": 0.10, "sweeper_actions": 0.05,
        "penalty_saves": 0.02, "pass_completion_rate": 0.05, "recovery_speed": 0.05,
    },
    "CB": {
        "defensive_actions": 0.35, "aerial_dominance": 0.15,
        "passing_distribution": 0.20, "ball_retention": 0.10,
        "positioning": 0.10, "discipline": 0.10,
    },
    "FB": {
        "defensive_actions": 0.25, "attacking_contribution": 0.20,
        "progressive_play": 0.15, "passing": 0.15,
        "work_rate": 0.10, "dribbling": 0.05, "discipline": 0.10,
    },
    "CDM": {
        "ball_winning": 0.30, "passing_distribution": 0.25,
        "ball_retention": 0.15, "positioning_coverage": 0.10,
        "aerial_ability": 0.05, "attacking_contribution": 0.05, "discipline": 0.10,
    },
    "CM": {
        "passing_creativity": 0.25, "ball_winning": 0.20,
        "progressive_play": 0.15, "work_rate": 0.10,
        "attacking_output": 0.10, "ball_retention": 0.10, "discipline": 0.10,
    },
    "CAM": {
        "creativity": 0.25, "goal_threat": 0.20,
        "dribbling": 0.15, "progressive_play": 0.15,
        "passing": 0.10, "work_rate": 0.10, "discipline": 0.05,
    },
    "W": {
        "attacking_output": 0.20, "crossing_delivery": 0.15,
        "dribbling": 0.20, "speed_dynamism": 0.10,
        "progressive_play": 0.10, "passing": 0.10,
        "defensive_contribution": 0.10, "discipline": 0.05,
    },
    "ST": {
        "goal_scoring": 0.30, "shot_quality": 0.15,
        "movement_positioning": 0.10, "aerial_ability": 0.10,
        "link_up_play": 0.10, "pressing_work_rate": 0.10,
        "dribbling": 0.10, "discipline": 0.05,
    },
}

# ---------------------------------------------------------------------------
# Universal metric definitions
# ---------------------------------------------------------------------------

METRIC_DEFINITIONS: dict[str, dict[str, Any]] = {
    # Passing
    "passes_attempted": {"label": "Passes Attempted", "unit": "count", "higher_is_better": True},
    "passes_completed": {"label": "Passes Completed", "unit": "count", "higher_is_better": True},
    "pass_completion_rate": {"label": "Pass Completion %", "unit": "percent", "higher_is_better": True},
    "key_passes": {"label": "Key Passes", "unit": "count", "higher_is_better": True},
    "through_balls": {"label": "Through Balls", "unit": "count", "higher_is_better": True},
    "long_passes_attempted": {"label": "Long Passes Attempted", "unit": "count", "higher_is_better": True},
    "long_passes_completed": {"label": "Long Passes Completed", "unit": "count", "higher_is_better": True},
    "crosses_attempted": {"label": "Crosses Attempted", "unit": "count", "higher_is_better": True},
    "crosses_completed": {"label": "Crosses Completed", "unit": "count", "higher_is_better": True},
    "assists": {"label": "Assists", "unit": "count", "higher_is_better": True},
    "progressive_passes": {"label": "Progressive Passes", "unit": "count", "higher_is_better": True},

    # Defensive
    "tackles_attempted": {"label": "Tackles Attempted", "unit": "count", "higher_is_better": True},
    "tackles_won": {"label": "Tackles Won", "unit": "count", "higher_is_better": True},
    "tackles_per_game": {"label": "Tackles Per Game", "unit": "count", "higher_is_better": True},
    "interceptions": {"label": "Interceptions", "unit": "count", "higher_is_better": True},
    "clearances": {"label": "Clearances", "unit": "count", "higher_is_better": True},
    "blocks": {"label": "Blocks", "unit": "count", "higher_is_better": True},
    "recoveries": {"label": "Ball Recoveries", "unit": "count", "higher_is_better": True},

    # Aerial
    "aerial_duels_won": {"label": "Aerial Duels Won", "unit": "count", "higher_is_better": True},
    "aerial_duels_lost": {"label": "Aerial Duels Lost", "unit": "count", "higher_is_better": False},
    "aerial_win_rate": {"label": "Aerial Win %", "unit": "percent", "higher_is_better": True},

    # Shooting
    "shots": {"label": "Shots", "unit": "count", "higher_is_better": True},
    "shots_on_target": {"label": "Shots on Target", "unit": "count", "higher_is_better": True},
    "goals": {"label": "Goals", "unit": "count", "higher_is_better": True},
    "xg": {"label": "Expected Goals (xG)", "unit": "float", "higher_is_better": True},

    # Dribbling
    "dribbles_attempted": {"label": "Dribbles Attempted", "unit": "count", "higher_is_better": True},
    "dribbles_completed": {"label": "Dribbles Completed", "unit": "count", "higher_is_better": True},
    "dribble_success_rate": {"label": "Dribble Success %", "unit": "percent", "higher_is_better": True},
    "progressive_carries": {"label": "Progressive Carries", "unit": "count", "higher_is_better": True},

    # Possession & Ball Retention
    "touches": {"label": "Touches", "unit": "count", "higher_is_better": True},
    "possession_time": {"label": "Possession Time", "unit": "seconds", "higher_is_better": True},
    "turnovers": {"label": "Turnovers", "unit": "count", "higher_is_better": False},
    "dispossessions": {"label": "Dispossessions", "unit": "count", "higher_is_better": False},
    "packing_points": {"label": "Packing Points", "unit": "count", "higher_is_better": True},

    # Physical / Athletic
    "distance_covered": {"label": "Distance Covered", "unit": "meters", "higher_is_better": True},
    "sprints": {"label": "Sprints", "unit": "count", "higher_is_better": True},
    "sprint_distance": {"label": "Sprint Distance", "unit": "meters", "higher_is_better": True},
    "top_speed": {"label": "Top Speed", "unit": "m/s", "higher_is_better": True},
    "high_intensity_runs": {"label": "High Intensity Runs", "unit": "count", "higher_is_better": True},
    "average_speed": {"label": "Average Speed", "unit": "m/s", "higher_is_better": True},

    # Discipline
    "fouls_committed": {"label": "Fouls Committed", "unit": "count", "higher_is_better": False},
    "fouls_drawn": {"label": "Fouls Drawn", "unit": "count", "higher_is_better": True},
    "yellow_cards": {"label": "Yellow Cards", "unit": "count", "higher_is_better": False},
    "red_cards": {"label": "Red Cards", "unit": "count", "higher_is_better": False},
    "offsides": {"label": "Offsides", "unit": "count", "higher_is_better": False},

    # Goalkeeper-specific
    "saves": {"label": "Saves", "unit": "count", "higher_is_better": True},
    "save_percentage": {"label": "Save %", "unit": "percent", "higher_is_better": True},
    "goals_conceded": {"label": "Goals Conceded", "unit": "count", "higher_is_better": False},
    "goals_against_avg": {"label": "Goals Against Avg", "unit": "float", "higher_is_better": False},
    "clean_sheet": {"label": "Clean Sheet", "unit": "boolean", "higher_is_better": True},
    "catches": {"label": "Catches", "unit": "count", "higher_is_better": True},
    "punches": {"label": "Punches", "unit": "count", "higher_is_better": True},
    "distribution_accuracy": {"label": "Distribution Accuracy %", "unit": "percent", "higher_is_better": True},
    "sweeper_actions": {"label": "Sweeper Actions", "unit": "count", "higher_is_better": True},
    "penalty_saves": {"label": "Penalty Saves", "unit": "count", "higher_is_better": True},
    "recovery_speed": {"label": "Recovery Speed", "unit": "m/s", "higher_is_better": True},

    # Bonus-eligible events
    "own_goals": {"label": "Own Goals", "unit": "count", "higher_is_better": False},
}

# ---------------------------------------------------------------------------
# Mapping from individual metrics into position-weight categories
# ---------------------------------------------------------------------------

CATEGORY_METRIC_MAP: dict[str, list[str]] = {
    # Goalkeeper categories
    "saves": ["saves"],
    "save_percentage": ["save_percentage"],
    "goals_conceded": ["goals_conceded"],
    "goals_against_avg": ["goals_against_avg"],
    "clean_sheet": ["clean_sheet"],
    "catches": ["catches"],
    "punches": ["punches"],
    "distribution_accuracy": ["distribution_accuracy"],
    "sweeper_actions": ["sweeper_actions"],
    "penalty_saves": ["penalty_saves"],
    "recovery_speed": ["recovery_speed"],

    # Outfield categories
    "defensive_actions": ["tackles_won", "interceptions", "clearances", "blocks", "recoveries"],
    "aerial_dominance": ["aerial_duels_won", "aerial_win_rate"],
    "aerial_ability": ["aerial_duels_won", "aerial_win_rate"],
    "passing_distribution": ["passes_completed", "pass_completion_rate", "long_passes_completed", "progressive_passes"],
    "ball_retention": ["touches", "possession_time", "turnovers", "dispossessions"],
    "positioning": ["recoveries", "interceptions"],
    "positioning_coverage": ["recoveries", "interceptions", "distance_covered"],
    "discipline": ["fouls_committed", "yellow_cards", "red_cards"],
    "attacking_contribution": ["goals", "assists", "shots_on_target", "key_passes"],
    "progressive_play": ["progressive_passes", "progressive_carries", "through_balls"],
    "passing": ["passes_completed", "pass_completion_rate", "key_passes"],
    "pass_completion_rate": ["pass_completion_rate"],
    "work_rate": ["distance_covered", "sprints", "high_intensity_runs"],
    "dribbling": ["dribbles_completed", "dribble_success_rate", "progressive_carries"],
    "ball_winning": ["tackles_won", "interceptions", "recoveries"],
    "passing_creativity": ["key_passes", "through_balls", "assists", "progressive_passes"],
    "attacking_output": ["goals", "assists", "shots_on_target", "key_passes", "xg"],
    "creativity": ["key_passes", "through_balls", "assists", "crosses_completed"],
    "goal_threat": ["goals", "shots_on_target", "xg"],
    "crossing_delivery": ["crosses_attempted", "crosses_completed"],
    "speed_dynamism": ["sprints", "top_speed", "sprint_distance", "high_intensity_runs"],
    "defensive_contribution": ["tackles_won", "interceptions", "recoveries"],
    "goal_scoring": ["goals", "xg", "shots_on_target"],
    "shot_quality": ["shots_on_target", "shots", "xg"],
    "movement_positioning": ["touches", "offsides"],
    "link_up_play": ["passes_completed", "key_passes", "dribbles_completed"],
    "pressing_work_rate": ["distance_covered", "sprints", "recoveries", "high_intensity_runs"],
}

# ---------------------------------------------------------------------------
# Age-group benchmark data (mean and std for key per-game metrics)
# ---------------------------------------------------------------------------

AGE_GROUP_BENCHMARKS: dict[str, dict[str, dict[str, float]]] = {
    "U8": {
        "pass_completion_rate": {"mean": 50.0, "std": 12.0},
        "tackles_per_game": {"mean": 4.0, "std": 1.5},
        "interceptions": {"mean": 2.0, "std": 1.0},
        "goals": {"mean": 0.8, "std": 0.6},
        "assists": {"mean": 0.3, "std": 0.3},
        "shots": {"mean": 2.5, "std": 1.5},
        "shots_on_target": {"mean": 1.0, "std": 0.8},
        "touches": {"mean": 25.0, "std": 10.0},
        "dribbles_completed": {"mean": 2.0, "std": 1.2},
        "dribble_success_rate": {"mean": 40.0, "std": 15.0},
        "distance_covered": {"mean": 2500.0, "std": 600.0},
        "sprints": {"mean": 8.0, "std": 3.0},
        "passes_completed": {"mean": 8.0, "std": 4.0},
        "key_passes": {"mean": 0.5, "std": 0.4},
        "turnovers": {"mean": 5.0, "std": 2.0},
        "fouls_committed": {"mean": 1.5, "std": 1.0},
        "clearances": {"mean": 2.0, "std": 1.2},
        "aerial_duels_won": {"mean": 0.5, "std": 0.5},
        "recoveries": {"mean": 3.0, "std": 1.5},
        "progressive_passes": {"mean": 1.5, "std": 1.0},
        "progressive_carries": {"mean": 1.5, "std": 1.0},
        "packing_points": {"mean": 3.0, "std": 2.0},
        "possession_time": {"mean": 30.0, "std": 12.0},
        "saves": {"mean": 3.0, "std": 1.5},
        "save_percentage": {"mean": 55.0, "std": 15.0},
        "goals_conceded": {"mean": 2.5, "std": 1.5},
        "yellow_cards": {"mean": 0.1, "std": 0.15},
        "red_cards": {"mean": 0.01, "std": 0.05},
        "xg": {"mean": 0.5, "std": 0.4},
        "top_speed": {"mean": 4.5, "std": 0.8},
        "crosses_completed": {"mean": 0.3, "std": 0.3},
        "through_balls": {"mean": 0.2, "std": 0.2},
        "blocks": {"mean": 0.8, "std": 0.6},
        "dispossessions": {"mean": 3.0, "std": 1.5},
        "high_intensity_runs": {"mean": 5.0, "std": 2.5},
    },
    "U10": {
        "pass_completion_rate": {"mean": 55.0, "std": 11.0},
        "tackles_per_game": {"mean": 4.5, "std": 1.5},
        "interceptions": {"mean": 2.5, "std": 1.2},
        "goals": {"mean": 0.7, "std": 0.5},
        "assists": {"mean": 0.4, "std": 0.3},
        "shots": {"mean": 2.5, "std": 1.4},
        "shots_on_target": {"mean": 1.2, "std": 0.8},
        "touches": {"mean": 30.0, "std": 10.0},
        "dribbles_completed": {"mean": 2.5, "std": 1.3},
        "dribble_success_rate": {"mean": 45.0, "std": 14.0},
        "distance_covered": {"mean": 3200.0, "std": 700.0},
        "sprints": {"mean": 10.0, "std": 3.5},
        "passes_completed": {"mean": 12.0, "std": 5.0},
        "key_passes": {"mean": 0.7, "std": 0.5},
        "turnovers": {"mean": 4.5, "std": 1.8},
        "fouls_committed": {"mean": 1.5, "std": 1.0},
        "clearances": {"mean": 2.5, "std": 1.3},
        "aerial_duels_won": {"mean": 0.8, "std": 0.6},
        "recoveries": {"mean": 3.5, "std": 1.5},
        "progressive_passes": {"mean": 2.0, "std": 1.2},
        "progressive_carries": {"mean": 2.0, "std": 1.2},
        "packing_points": {"mean": 5.0, "std": 2.5},
        "possession_time": {"mean": 40.0, "std": 15.0},
        "saves": {"mean": 3.5, "std": 1.5},
        "save_percentage": {"mean": 58.0, "std": 14.0},
        "goals_conceded": {"mean": 2.0, "std": 1.3},
        "yellow_cards": {"mean": 0.15, "std": 0.18},
        "red_cards": {"mean": 0.01, "std": 0.05},
        "xg": {"mean": 0.5, "std": 0.4},
        "top_speed": {"mean": 5.0, "std": 0.8},
        "crosses_completed": {"mean": 0.5, "std": 0.4},
        "through_balls": {"mean": 0.3, "std": 0.3},
        "blocks": {"mean": 1.0, "std": 0.7},
        "dispossessions": {"mean": 3.0, "std": 1.5},
        "high_intensity_runs": {"mean": 6.0, "std": 2.5},
    },
    "U12": {
        "pass_completion_rate": {"mean": 60.0, "std": 10.0},
        "tackles_per_game": {"mean": 5.0, "std": 1.8},
        "interceptions": {"mean": 3.0, "std": 1.3},
        "goals": {"mean": 0.6, "std": 0.5},
        "assists": {"mean": 0.4, "std": 0.3},
        "shots": {"mean": 2.5, "std": 1.3},
        "shots_on_target": {"mean": 1.3, "std": 0.8},
        "touches": {"mean": 35.0, "std": 12.0},
        "dribbles_completed": {"mean": 3.0, "std": 1.4},
        "dribble_success_rate": {"mean": 48.0, "std": 13.0},
        "distance_covered": {"mean": 4200.0, "std": 800.0},
        "sprints": {"mean": 12.0, "std": 4.0},
        "passes_completed": {"mean": 16.0, "std": 6.0},
        "key_passes": {"mean": 0.9, "std": 0.6},
        "turnovers": {"mean": 4.0, "std": 1.8},
        "fouls_committed": {"mean": 1.8, "std": 1.0},
        "clearances": {"mean": 3.0, "std": 1.5},
        "aerial_duels_won": {"mean": 1.2, "std": 0.8},
        "recoveries": {"mean": 4.0, "std": 1.8},
        "progressive_passes": {"mean": 3.0, "std": 1.5},
        "progressive_carries": {"mean": 2.5, "std": 1.3},
        "packing_points": {"mean": 7.0, "std": 3.0},
        "possession_time": {"mean": 50.0, "std": 18.0},
        "saves": {"mean": 3.5, "std": 1.6},
        "save_percentage": {"mean": 60.0, "std": 13.0},
        "goals_conceded": {"mean": 1.8, "std": 1.2},
        "yellow_cards": {"mean": 0.2, "std": 0.2},
        "red_cards": {"mean": 0.02, "std": 0.06},
        "xg": {"mean": 0.5, "std": 0.4},
        "top_speed": {"mean": 5.5, "std": 0.9},
        "crosses_completed": {"mean": 0.7, "std": 0.5},
        "through_balls": {"mean": 0.4, "std": 0.3},
        "blocks": {"mean": 1.2, "std": 0.8},
        "dispossessions": {"mean": 2.8, "std": 1.4},
        "high_intensity_runs": {"mean": 8.0, "std": 3.0},
    },
    "U14": {
        "pass_completion_rate": {"mean": 65.0, "std": 9.0},
        "tackles_per_game": {"mean": 5.5, "std": 2.0},
        "interceptions": {"mean": 3.5, "std": 1.5},
        "goals": {"mean": 0.5, "std": 0.5},
        "assists": {"mean": 0.4, "std": 0.3},
        "shots": {"mean": 2.2, "std": 1.2},
        "shots_on_target": {"mean": 1.2, "std": 0.7},
        "touches": {"mean": 40.0, "std": 13.0},
        "dribbles_completed": {"mean": 3.0, "std": 1.5},
        "dribble_success_rate": {"mean": 50.0, "std": 12.0},
        "distance_covered": {"mean": 5500.0, "std": 900.0},
        "sprints": {"mean": 15.0, "std": 4.5},
        "passes_completed": {"mean": 20.0, "std": 7.0},
        "key_passes": {"mean": 1.0, "std": 0.6},
        "turnovers": {"mean": 3.5, "std": 1.5},
        "fouls_committed": {"mean": 1.8, "std": 1.0},
        "clearances": {"mean": 3.5, "std": 1.6},
        "aerial_duels_won": {"mean": 1.5, "std": 1.0},
        "recoveries": {"mean": 4.5, "std": 2.0},
        "progressive_passes": {"mean": 3.5, "std": 1.6},
        "progressive_carries": {"mean": 3.0, "std": 1.5},
        "packing_points": {"mean": 9.0, "std": 3.5},
        "possession_time": {"mean": 60.0, "std": 20.0},
        "saves": {"mean": 4.0, "std": 1.8},
        "save_percentage": {"mean": 63.0, "std": 12.0},
        "goals_conceded": {"mean": 1.5, "std": 1.0},
        "yellow_cards": {"mean": 0.25, "std": 0.22},
        "red_cards": {"mean": 0.02, "std": 0.06},
        "xg": {"mean": 0.45, "std": 0.35},
        "top_speed": {"mean": 6.0, "std": 0.9},
        "crosses_completed": {"mean": 0.8, "std": 0.5},
        "through_balls": {"mean": 0.5, "std": 0.4},
        "blocks": {"mean": 1.5, "std": 0.9},
        "dispossessions": {"mean": 2.5, "std": 1.3},
        "high_intensity_runs": {"mean": 10.0, "std": 3.5},
    },
    "U16": {
        "pass_completion_rate": {"mean": 70.0, "std": 8.0},
        "tackles_per_game": {"mean": 5.5, "std": 2.0},
        "interceptions": {"mean": 3.5, "std": 1.5},
        "goals": {"mean": 0.45, "std": 0.45},
        "assists": {"mean": 0.35, "std": 0.3},
        "shots": {"mean": 2.0, "std": 1.1},
        "shots_on_target": {"mean": 1.1, "std": 0.7},
        "touches": {"mean": 45.0, "std": 14.0},
        "dribbles_completed": {"mean": 3.0, "std": 1.5},
        "dribble_success_rate": {"mean": 52.0, "std": 11.0},
        "distance_covered": {"mean": 7000.0, "std": 1000.0},
        "sprints": {"mean": 18.0, "std": 5.0},
        "passes_completed": {"mean": 25.0, "std": 8.0},
        "key_passes": {"mean": 1.1, "std": 0.7},
        "turnovers": {"mean": 3.0, "std": 1.3},
        "fouls_committed": {"mean": 2.0, "std": 1.0},
        "clearances": {"mean": 3.5, "std": 1.6},
        "aerial_duels_won": {"mean": 2.0, "std": 1.2},
        "recoveries": {"mean": 5.0, "std": 2.0},
        "progressive_passes": {"mean": 4.0, "std": 1.8},
        "progressive_carries": {"mean": 3.0, "std": 1.5},
        "packing_points": {"mean": 11.0, "std": 4.0},
        "possession_time": {"mean": 65.0, "std": 20.0},
        "saves": {"mean": 4.0, "std": 1.8},
        "save_percentage": {"mean": 65.0, "std": 11.0},
        "goals_conceded": {"mean": 1.3, "std": 0.9},
        "yellow_cards": {"mean": 0.3, "std": 0.25},
        "red_cards": {"mean": 0.03, "std": 0.07},
        "xg": {"mean": 0.4, "std": 0.35},
        "top_speed": {"mean": 6.8, "std": 0.9},
        "crosses_completed": {"mean": 1.0, "std": 0.6},
        "through_balls": {"mean": 0.6, "std": 0.4},
        "blocks": {"mean": 1.5, "std": 0.9},
        "dispossessions": {"mean": 2.2, "std": 1.2},
        "high_intensity_runs": {"mean": 12.0, "std": 4.0},
    },
    "U18": {
        "pass_completion_rate": {"mean": 74.0, "std": 7.0},
        "tackles_per_game": {"mean": 5.5, "std": 2.0},
        "interceptions": {"mean": 3.5, "std": 1.5},
        "goals": {"mean": 0.4, "std": 0.4},
        "assists": {"mean": 0.35, "std": 0.3},
        "shots": {"mean": 2.0, "std": 1.0},
        "shots_on_target": {"mean": 1.1, "std": 0.7},
        "touches": {"mean": 50.0, "std": 15.0},
        "dribbles_completed": {"mean": 3.0, "std": 1.5},
        "dribble_success_rate": {"mean": 54.0, "std": 10.0},
        "distance_covered": {"mean": 8500.0, "std": 1200.0},
        "sprints": {"mean": 20.0, "std": 5.5},
        "passes_completed": {"mean": 30.0, "std": 9.0},
        "key_passes": {"mean": 1.2, "std": 0.7},
        "turnovers": {"mean": 2.8, "std": 1.2},
        "fouls_committed": {"mean": 2.0, "std": 1.0},
        "clearances": {"mean": 3.5, "std": 1.6},
        "aerial_duels_won": {"mean": 2.5, "std": 1.3},
        "recoveries": {"mean": 5.5, "std": 2.2},
        "progressive_passes": {"mean": 4.5, "std": 2.0},
        "progressive_carries": {"mean": 3.5, "std": 1.6},
        "packing_points": {"mean": 13.0, "std": 4.5},
        "possession_time": {"mean": 70.0, "std": 22.0},
        "saves": {"mean": 4.0, "std": 2.0},
        "save_percentage": {"mean": 68.0, "std": 10.0},
        "goals_conceded": {"mean": 1.2, "std": 0.8},
        "yellow_cards": {"mean": 0.35, "std": 0.28},
        "red_cards": {"mean": 0.03, "std": 0.07},
        "xg": {"mean": 0.4, "std": 0.3},
        "top_speed": {"mean": 7.5, "std": 1.0},
        "crosses_completed": {"mean": 1.2, "std": 0.7},
        "through_balls": {"mean": 0.7, "std": 0.5},
        "blocks": {"mean": 1.8, "std": 1.0},
        "dispossessions": {"mean": 2.0, "std": 1.1},
        "high_intensity_runs": {"mean": 14.0, "std": 4.5},
    },
}

# Provide aliases so that odd age groups (U9, U11, ...) fall back to the
# nearest defined benchmark group.
_AGE_ALIAS: dict[str, str] = {
    "U8": "U8", "U9": "U8",
    "U10": "U10", "U11": "U10",
    "U12": "U12", "U13": "U12",
    "U14": "U14", "U15": "U14",
    "U16": "U16", "U17": "U16",
    "U18": "U18", "U19": "U18",
}

# ---------------------------------------------------------------------------
# Event type constants that appear in TrackingEvent.event_type
# ---------------------------------------------------------------------------

EVENT_TYPES = {
    "pass_attempted", "pass_completed", "pass_incomplete",
    "long_pass_attempted", "long_pass_completed",
    "cross_attempted", "cross_completed",
    "through_ball",
    "tackle_attempted", "tackle_won",
    "interception", "clearance", "block", "recovery",
    "shot", "shot_on_target", "goal",
    "dribble_attempted", "dribble_completed",
    "aerial_duel_won", "aerial_duel_lost",
    "touch",
    "turnover", "dispossession",
    "foul_committed", "foul_drawn",
    "yellow_card", "red_card",
    "offside",
    "sprint",
    "key_pass", "assist",
    "progressive_pass", "progressive_carry",
    "save", "catch", "punch", "sweeper_action", "penalty_save",
    "own_goal",
    "position_sample",  # periodic x/y for distance & speed
}


class StatsEngine:
    """Compute player and team statistics from tracking event data."""

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_player_stats(
        self,
        tracking_events: list[dict[str, Any]],
        player_id: int,
        game_duration: float,
    ) -> dict[str, float]:
        """Aggregate tracking events for a single player into per-game stats.

        Parameters
        ----------
        tracking_events:
            List of tracking event dicts (or ORM objects serialised to dicts)
            filtered to this player.  Each must have at minimum
            ``event_type``, ``timestamp_seconds``, and optionally ``x_position``,
            ``y_position``, ``metadata``.
        player_id:
            The player's database id (used only for logging).
        game_duration:
            Total game duration in minutes.

        Returns
        -------
        dict mapping metric_name -> metric_value.
        """
        stats: dict[str, float] = {}

        # Count events by type
        counts: dict[str, int] = defaultdict(int)
        positions: list[tuple[float, float, float]] = []  # (t, x, y)

        for evt in tracking_events:
            etype = evt.get("event_type", "")
            counts[etype] += 1

            x = evt.get("x_position")
            y = evt.get("y_position")
            t = evt.get("timestamp_seconds", 0.0)
            if etype == "position_sample" and x is not None and y is not None:
                positions.append((t, x, y))

        # ------ Passing ------
        stats["passes_attempted"] = float(counts.get("pass_attempted", 0))
        stats["passes_completed"] = float(counts.get("pass_completed", 0))
        if stats["passes_attempted"] > 0:
            stats["pass_completion_rate"] = (
                stats["passes_completed"] / stats["passes_attempted"] * 100.0
            )
        else:
            stats["pass_completion_rate"] = 0.0
        stats["key_passes"] = float(counts.get("key_pass", 0))
        stats["through_balls"] = float(counts.get("through_ball", 0))
        stats["long_passes_attempted"] = float(counts.get("long_pass_attempted", 0))
        stats["long_passes_completed"] = float(counts.get("long_pass_completed", 0))
        stats["crosses_attempted"] = float(counts.get("cross_attempted", 0))
        stats["crosses_completed"] = float(counts.get("cross_completed", 0))
        stats["assists"] = float(counts.get("assist", 0))
        stats["progressive_passes"] = float(counts.get("progressive_pass", 0))

        # ------ Defensive ------
        stats["tackles_attempted"] = float(counts.get("tackle_attempted", 0))
        stats["tackles_won"] = float(counts.get("tackle_won", 0))
        if game_duration > 0:
            stats["tackles_per_game"] = stats["tackles_won"]  # already per-game
        else:
            stats["tackles_per_game"] = 0.0
        stats["interceptions"] = float(counts.get("interception", 0))
        stats["clearances"] = float(counts.get("clearance", 0))
        stats["blocks"] = float(counts.get("block", 0))
        stats["recoveries"] = float(counts.get("recovery", 0))

        # ------ Aerial ------
        stats["aerial_duels_won"] = float(counts.get("aerial_duel_won", 0))
        stats["aerial_duels_lost"] = float(counts.get("aerial_duel_lost", 0))
        aerial_total = stats["aerial_duels_won"] + stats["aerial_duels_lost"]
        if aerial_total > 0:
            stats["aerial_win_rate"] = stats["aerial_duels_won"] / aerial_total * 100.0
        else:
            stats["aerial_win_rate"] = 0.0

        # ------ Shooting ------
        stats["shots"] = float(counts.get("shot", 0) + counts.get("shot_on_target", 0) + counts.get("goal", 0))
        stats["shots_on_target"] = float(counts.get("shot_on_target", 0) + counts.get("goal", 0))
        stats["goals"] = float(counts.get("goal", 0))

        # xG placeholder -- in production this is computed per-shot
        meta_xg = self._sum_metadata_field(tracking_events, "shot", "xg")
        meta_xg += self._sum_metadata_field(tracking_events, "shot_on_target", "xg")
        meta_xg += self._sum_metadata_field(tracking_events, "goal", "xg")
        stats["xg"] = meta_xg if meta_xg > 0 else stats["shots_on_target"] * 0.35

        # ------ Dribbling ------
        stats["dribbles_attempted"] = float(counts.get("dribble_attempted", 0))
        stats["dribbles_completed"] = float(counts.get("dribble_completed", 0))
        if stats["dribbles_attempted"] > 0:
            stats["dribble_success_rate"] = (
                stats["dribbles_completed"] / stats["dribbles_attempted"] * 100.0
            )
        else:
            stats["dribble_success_rate"] = 0.0
        stats["progressive_carries"] = float(counts.get("progressive_carry", 0))

        # ------ Possession & Ball Retention ------
        stats["touches"] = float(counts.get("touch", 0))
        stats["possession_time"] = self._compute_possession_time(tracking_events)
        stats["turnovers"] = float(counts.get("turnover", 0))
        stats["dispossessions"] = float(counts.get("dispossession", 0))
        stats["packing_points"] = self._sum_metadata_field(
            tracking_events, "pass_completed", "packing"
        )

        # ------ Physical / Athletic ------
        distance, top_speed, avg_speed = self._compute_physical_metrics(positions)
        stats["distance_covered"] = distance
        stats["top_speed"] = top_speed
        stats["average_speed"] = avg_speed
        stats["sprints"] = float(counts.get("sprint", 0))
        stats["sprint_distance"] = self._sum_metadata_field(
            tracking_events, "sprint", "distance"
        )
        stats["high_intensity_runs"] = max(
            stats["sprints"] * 0.7,
            self._sum_metadata_field(tracking_events, "sprint", "high_intensity"),
        )

        # ------ Discipline ------
        stats["fouls_committed"] = float(counts.get("foul_committed", 0))
        stats["fouls_drawn"] = float(counts.get("foul_drawn", 0))
        stats["yellow_cards"] = float(counts.get("yellow_card", 0))
        stats["red_cards"] = float(counts.get("red_card", 0))
        stats["offsides"] = float(counts.get("offside", 0))

        # ------ Goalkeeper-specific ------
        stats["saves"] = float(counts.get("save", 0))
        shots_faced = stats["saves"] + float(counts.get("goal", 0))
        if shots_faced > 0:
            stats["save_percentage"] = stats["saves"] / shots_faced * 100.0
        else:
            stats["save_percentage"] = 0.0
        stats["goals_conceded"] = float(counts.get("goal", 0))
        if game_duration > 0:
            stats["goals_against_avg"] = stats["goals_conceded"] / (game_duration / 90.0)
        else:
            stats["goals_against_avg"] = 0.0
        stats["clean_sheet"] = 1.0 if stats["goals_conceded"] == 0 else 0.0
        stats["catches"] = float(counts.get("catch", 0))
        stats["punches"] = float(counts.get("punch", 0))
        stats["distribution_accuracy"] = stats["pass_completion_rate"]  # proxy
        stats["sweeper_actions"] = float(counts.get("sweeper_action", 0))
        stats["penalty_saves"] = float(counts.get("penalty_save", 0))
        stats["recovery_speed"] = avg_speed  # proxy

        # ------ Bonus-eligible ------
        stats["own_goals"] = float(counts.get("own_goal", 0))

        logger.debug(
            "Computed %d metrics for player_id=%d over %.1f min",
            len(stats), player_id, game_duration,
        )
        return stats

    def compute_team_stats(
        self,
        all_player_stats: dict[int, dict[str, float]],
        game_data: dict[str, Any],
    ) -> dict[str, float]:
        """Aggregate individual player stats into team-level metrics.

        Parameters
        ----------
        all_player_stats:
            Mapping of player_id -> stat dict (output of ``compute_player_stats``).
        game_data:
            Auxiliary game information (score, duration, etc.).

        Returns
        -------
        dict of team-level metric name -> value.
        """
        team: dict[str, float] = {}

        # Summable metrics
        summable = [
            "passes_attempted", "passes_completed", "shots", "shots_on_target",
            "goals", "assists", "tackles_won", "interceptions", "clearances",
            "fouls_committed", "yellow_cards", "red_cards", "turnovers",
            "dribbles_completed", "crosses_completed", "key_passes",
            "progressive_passes", "progressive_carries", "recoveries",
            "aerial_duels_won", "aerial_duels_lost", "packing_points",
        ]
        for metric in summable:
            team[f"total_{metric}"] = sum(
                ps.get(metric, 0.0) for ps in all_player_stats.values()
            )

        # Averageable metrics
        n_players = max(len(all_player_stats), 1)
        averageable = ["pass_completion_rate", "dribble_success_rate", "distance_covered"]
        for metric in averageable:
            team[f"avg_{metric}"] = (
                sum(ps.get(metric, 0.0) for ps in all_player_stats.values()) / n_players
            )

        # Derived
        if team.get("total_passes_attempted", 0) > 0:
            team["team_pass_completion_rate"] = (
                team["total_passes_completed"]
                / team["total_passes_attempted"]
                * 100.0
            )
        else:
            team["team_pass_completion_rate"] = 0.0

        total_aerial = (
            team.get("total_aerial_duels_won", 0)
            + team.get("total_aerial_duels_lost", 0)
        )
        if total_aerial > 0:
            team["team_aerial_win_rate"] = (
                team["total_aerial_duels_won"] / total_aerial * 100.0
            )
        else:
            team["team_aerial_win_rate"] = 0.0

        # Distance / physical totals
        team["total_distance_covered"] = sum(
            ps.get("distance_covered", 0.0) for ps in all_player_stats.values()
        )
        team["total_sprints"] = sum(
            ps.get("sprints", 0.0) for ps in all_player_stats.values()
        )

        # Game-level
        team["score_home"] = float(game_data.get("score_home", 0))
        team["score_away"] = float(game_data.get("score_away", 0))
        team["game_duration_minutes"] = float(game_data.get("duration_minutes", 0))

        return team

    def categorize_metrics(
        self,
        stats: dict[str, float],
        position_group: str,
    ) -> dict[str, list[str]]:
        """Group available metrics into scoring categories for a position.

        Returns a dict of category_name -> list of metric names present in
        *stats* that belong to that category.
        """
        weights = POSITION_WEIGHTS.get(position_group, POSITION_WEIGHTS["CM"])
        result: dict[str, list[str]] = {}

        for category in weights:
            metric_names = CATEGORY_METRIC_MAP.get(category, [])
            present = [m for m in metric_names if m in stats]
            if present:
                result[category] = present

        return result

    def get_metric_category(
        self,
        metric_name: str,
        position_group: str,
    ) -> Optional[str]:
        """Return the scoring category a metric belongs to for the position.

        Returns ``None`` if the metric is not mapped to any category used by
        the given position group.
        """
        weights = POSITION_WEIGHTS.get(position_group, POSITION_WEIGHTS["CM"])
        for category in weights:
            metric_names = CATEGORY_METRIC_MAP.get(category, [])
            if metric_name in metric_names:
                return category
        return None

    @staticmethod
    def get_benchmarks(age_group: str) -> dict[str, dict[str, float]]:
        """Return benchmark data for the given age group.

        Falls back to the nearest defined age group when the exact one is
        not present.
        """
        key = _AGE_ALIAS.get(age_group, "U14")
        return AGE_GROUP_BENCHMARKS.get(key, AGE_GROUP_BENCHMARKS["U14"])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _sum_metadata_field(
        events: list[dict[str, Any]],
        event_type: str,
        field: str,
    ) -> float:
        """Sum a numeric field from event metadata for a given event type."""
        total = 0.0
        for evt in events:
            if evt.get("event_type") == event_type:
                meta = evt.get("metadata") or {}
                val = meta.get(field)
                if val is not None:
                    total += float(val)
        return total

    @staticmethod
    def _compute_physical_metrics(
        positions: list[tuple[float, float, float]],
    ) -> tuple[float, float, float]:
        """Compute distance, top speed, and average speed from position samples.

        Parameters
        ----------
        positions:
            Sorted list of ``(timestamp_seconds, x, y)`` tuples.

        Returns
        -------
        (total_distance_meters, top_speed_m_s, avg_speed_m_s)
        """
        if len(positions) < 2:
            return 0.0, 0.0, 0.0

        positions_sorted = sorted(positions, key=lambda p: p[0])
        total_distance = 0.0
        top_speed = 0.0
        speeds: list[float] = []

        for i in range(1, len(positions_sorted)):
            t0, x0, y0 = positions_sorted[i - 1]
            t1, x1, y1 = positions_sorted[i]
            dt = t1 - t0
            if dt <= 0:
                continue
            dx = x1 - x0
            dy = y1 - y0
            dist = np.sqrt(dx * dx + dy * dy)
            total_distance += dist
            speed = dist / dt
            speeds.append(speed)
            if speed > top_speed:
                top_speed = speed

        avg_speed = float(np.mean(speeds)) if speeds else 0.0
        return total_distance, top_speed, avg_speed

    @staticmethod
    def _compute_possession_time(events: list[dict[str, Any]]) -> float:
        """Estimate possession time in seconds from touch/pass events."""
        touch_events = [
            e for e in events
            if e.get("event_type") in {
                "touch", "pass_attempted", "pass_completed",
                "dribble_attempted", "dribble_completed",
            }
        ]
        if len(touch_events) < 2:
            return 0.0

        touch_events.sort(key=lambda e: e.get("timestamp_seconds", 0.0))
        total = 0.0
        for i in range(1, len(touch_events)):
            dt = (
                touch_events[i].get("timestamp_seconds", 0.0)
                - touch_events[i - 1].get("timestamp_seconds", 0.0)
            )
            # Only count gaps shorter than 10 seconds as continuous possession
            if 0 < dt <= 10.0:
                total += dt
        return total
