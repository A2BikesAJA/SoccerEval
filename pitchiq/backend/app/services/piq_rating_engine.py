from __future__ import annotations

"""PIQ Rating Engine -- computes the persistent 1-99 OVR rating.

The PIQ Rating is built from 29 sub-attributes grouped under 6 face-card
attributes (SPD, SHT, PAS, DRB, DEF, PHY).  Sub-attribute values are derived
from a rolling window of recent game stats, recency-weighted and normalised
against age-group benchmarks.  The Overall (OVR) rating is then computed
using position-specific coefficients and optionally adjusted for
competition tier.
"""

from __future__ import annotations

import logging
from datetime import date
from typing import Any, Optional

import numpy as np
from scipy import stats as scipy_stats
from sqlalchemy.orm import Session

from app.config import settings
from app.models.scores import PIQConfidenceLevel, PIQRating, PIQRatingHistory
from app.models.stats import PlayerGameStats
from app.models.game_player import GamePlayer
from app.models.game import Game
from app.services.stats_engine import AGE_GROUP_BENCHMARKS, StatsEngine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 29 sub-attributes organised under 6 face-card attributes
# ---------------------------------------------------------------------------

SUB_ATTRIBUTE_MAP: dict[str, list[str]] = {
    "spd": ["sprint_speed", "acceleration", "off_ball_movement", "recovery_runs", "agility"],
    "sht": ["finishing", "shot_power", "long_shots", "positioning_attack", "volleys_headers"],
    "pas": ["short_passing", "long_passing", "crossing", "vision", "free_kick_delivery"],
    "drb": ["ball_control", "dribbling_skill", "composure", "flair", "balance"],
    "def": ["standing_tackle", "interceptions", "heading_accuracy", "marking", "defensive_awareness"],
    "phy": ["stamina", "strength", "aggression", "jumping"],
}

# ---------------------------------------------------------------------------
# Face-card attribute weights (one weight per sub-attribute, in order)
# ---------------------------------------------------------------------------

FACE_CARD_WEIGHTS: dict[str, list[float]] = {
    "spd": [0.30, 0.25, 0.20, 0.15, 0.10],
    "sht": [0.35, 0.20, 0.15, 0.20, 0.10],
    "pas": [0.25, 0.20, 0.15, 0.25, 0.15],
    "drb": [0.25, 0.30, 0.20, 0.15, 0.10],
    "def": [0.25, 0.25, 0.15, 0.15, 0.20],
    "phy": [0.30, 0.25, 0.25, 0.20],
}

# ---------------------------------------------------------------------------
# OVR positional coefficients
# ---------------------------------------------------------------------------

OVR_COEFFICIENTS: dict[str, dict[str, float]] = {
    "GK":  {"spd": 0.05, "sht": 0.00, "pas": 0.15, "drb": 0.05, "def": 0.10, "phy": 0.15, "gk": 0.50},
    "CB":  {"spd": 0.05, "sht": 0.03, "pas": 0.18, "drb": 0.07, "def": 0.40, "phy": 0.27},
    "FB":  {"spd": 0.15, "sht": 0.05, "pas": 0.17, "drb": 0.10, "def": 0.28, "phy": 0.25},
    "CDM": {"spd": 0.08, "sht": 0.05, "pas": 0.25, "drb": 0.10, "def": 0.30, "phy": 0.22},
    "CM":  {"spd": 0.10, "sht": 0.12, "pas": 0.25, "drb": 0.15, "def": 0.15, "phy": 0.23},
    "CAM": {"spd": 0.12, "sht": 0.22, "pas": 0.22, "drb": 0.20, "def": 0.05, "phy": 0.19},
    "W":   {"spd": 0.20, "sht": 0.18, "pas": 0.15, "drb": 0.22, "def": 0.08, "phy": 0.17},
    "ST":  {"spd": 0.15, "sht": 0.30, "pas": 0.10, "drb": 0.15, "def": 0.05, "phy": 0.25},
}

# ---------------------------------------------------------------------------
# Mapping from game stats -> sub-attribute derivation
# Each sub-attribute is derived from one or more game-level metrics with a
# simple weighted average.  The percentiles are against age-group benchmarks.
# ---------------------------------------------------------------------------

_SUB_ATTR_STAT_MAP: dict[str, list[tuple[str, float]]] = {
    # --- Speed ---
    "sprint_speed":     [("top_speed", 1.0)],
    "acceleration":     [("sprints", 0.5), ("top_speed", 0.5)],
    "off_ball_movement": [("distance_covered", 0.4), ("touches", 0.3), ("progressive_carries", 0.3)],
    "recovery_runs":    [("recoveries", 0.6), ("distance_covered", 0.4)],
    "agility":          [("dribble_success_rate", 0.5), ("top_speed", 0.3), ("sprints", 0.2)],

    # --- Shooting ---
    "finishing":         [("goals", 0.5), ("xg", 0.3), ("shots_on_target", 0.2)],
    "shot_power":        [("shots_on_target", 0.5), ("shots", 0.5)],
    "long_shots":        [("shots", 0.5), ("xg", 0.5)],
    "positioning_attack": [("touches", 0.3), ("goals", 0.4), ("xg", 0.3)],
    "volleys_headers":   [("aerial_duels_won", 0.5), ("goals", 0.5)],

    # --- Passing ---
    "short_passing":     [("pass_completion_rate", 0.6), ("passes_completed", 0.4)],
    "long_passing":      [("long_passes_completed", 0.7), ("progressive_passes", 0.3)],
    "crossing":          [("crosses_completed", 1.0)],
    "vision":            [("key_passes", 0.4), ("through_balls", 0.3), ("assists", 0.3)],
    "free_kick_delivery": [("crosses_completed", 0.5), ("key_passes", 0.5)],

    # --- Dribbling ---
    "ball_control":      [("touches", 0.4), ("dribble_success_rate", 0.3), ("turnovers", 0.3)],
    "dribbling_skill":   [("dribbles_completed", 0.6), ("dribble_success_rate", 0.4)],
    "composure":         [("pass_completion_rate", 0.4), ("turnovers", 0.3), ("dispossessions", 0.3)],
    "flair":             [("dribbles_completed", 0.4), ("key_passes", 0.3), ("through_balls", 0.3)],
    "balance":           [("dribble_success_rate", 0.5), ("dispossessions", 0.5)],

    # --- Defending ---
    "standing_tackle":    [("tackles_won", 0.7), ("tackles_per_game", 0.3)],
    "interceptions":      [("interceptions", 1.0)],
    "heading_accuracy":   [("aerial_duels_won", 0.7), ("aerial_win_rate", 0.3)],
    "marking":            [("interceptions", 0.4), ("recoveries", 0.3), ("tackles_won", 0.3)],
    "defensive_awareness": [("interceptions", 0.3), ("recoveries", 0.3), ("clearances", 0.2), ("blocks", 0.2)],

    # --- Physicality ---
    "stamina":           [("distance_covered", 0.5), ("sprints", 0.3), ("high_intensity_runs", 0.2)],
    "strength":          [("aerial_duels_won", 0.4), ("tackles_won", 0.3), ("fouls_drawn", 0.3)],
    "aggression":        [("tackles_won", 0.3), ("fouls_committed", 0.3), ("recoveries", 0.4)],
    "jumping":           [("aerial_duels_won", 0.7), ("aerial_win_rate", 0.3)],
}

# Inverse metrics where a higher raw value should map to a *lower* sub-attribute
_INVERSE_STAT_METRICS: set[str] = {
    "turnovers", "dispossessions", "fouls_committed",
}


class PIQRatingEngine:
    """Compute and persist the PIQ Rating (1-99 OVR) for a player."""

    def __init__(self) -> None:
        self._stats_engine = StatsEngine()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compute_sub_attributes(
        self,
        game_stats_history: list[dict[str, float]],
        age_group: str,
    ) -> dict[str, int]:
        """Derive 29 sub-attribute values (1-99) from recent game stats.

        Parameters
        ----------
        game_stats_history:
            List of per-game stat dicts, ordered most-recent-first.
            At most ``settings.piq_rolling_window`` games are used.
        age_group:
            E.g. ``"U14"``.

        Returns
        -------
        Dict of sub_attribute_name -> value in [1, 99].
        """
        if not game_stats_history:
            # Return defaults (50) when there is no history
            return {attr: 50 for group in SUB_ATTRIBUTE_MAP.values() for attr in group}

        window = settings.piq_rolling_window
        recency_weights = settings.piq_recency_weights

        # Trim to rolling window
        games = game_stats_history[:window]
        n_games = len(games)

        # Build recency weight array (pad if needed)
        weights = np.array(
            recency_weights[:n_games]
            if n_games <= len(recency_weights)
            else recency_weights + [0.3] * (n_games - len(recency_weights))
        )
        weights = weights / weights.sum()  # normalise

        benchmarks = self._stats_engine.get_benchmarks(age_group)
        sub_attributes: dict[str, int] = {}

        for attr_name, stat_components in _SUB_ATTR_STAT_MAP.items():
            # Compute a weighted-average percentile for this sub-attribute
            per_game_scores: list[float] = []

            for game_stats in games:
                component_score = 0.0
                for stat_name, stat_weight in stat_components:
                    raw = game_stats.get(stat_name, 0.0)
                    pct = self._stat_to_percentile(raw, stat_name, benchmarks)
                    component_score += pct * stat_weight
                per_game_scores.append(component_score)

            # Recency-weighted average
            per_game_arr = np.array(per_game_scores[:n_games])
            weighted_avg = float(np.dot(per_game_arr, weights))

            # Map percentile (0-100) -> sub-attribute (1-99)
            value = int(round(max(1, min(99, weighted_avg * 0.99))))
            sub_attributes[attr_name] = value

        return sub_attributes

    def compute_face_card_attributes(
        self,
        sub_attributes: dict[str, int],
    ) -> dict[str, int]:
        """Compute the 6 face-card attributes from 29 sub-attributes.

        Each face-card attribute is a weighted average of its constituent
        sub-attributes using ``FACE_CARD_WEIGHTS``.

        Returns
        -------
        Dict of face_card_name -> value in [1, 99].
        """
        face_cards: dict[str, int] = {}

        for fc_name, sub_names in SUB_ATTRIBUTE_MAP.items():
            fc_weights = FACE_CARD_WEIGHTS[fc_name]
            values = [float(sub_attributes.get(s, 50)) for s in sub_names]
            weighted = sum(v * w for v, w in zip(values, fc_weights))
            face_cards[fc_name] = int(round(max(1, min(99, weighted))))

        return face_cards

    def compute_ovr(
        self,
        face_card_attributes: dict[str, int],
        position_group: str,
    ) -> int:
        """Compute Overall rating (1-99) from face-card attributes.

        Uses position-specific ``OVR_COEFFICIENTS``.

        Parameters
        ----------
        face_card_attributes:
            Dict with keys ``spd``, ``sht``, ``pas``, ``drb``, ``def``, ``phy``
            and optionally ``gk`` (for goalkeepers).
        position_group:
            One of GK, CB, FB, CDM, CM, CAM, W, ST.

        Returns
        -------
        int OVR in [1, 99].
        """
        coeffs = OVR_COEFFICIENTS.get(position_group, OVR_COEFFICIENTS["CM"])

        ovr_raw = 0.0
        for attr_key, coeff in coeffs.items():
            value = float(face_card_attributes.get(attr_key, 50))
            ovr_raw += value * coeff

        return int(round(max(1, min(99, ovr_raw))))

    def update_piq_rating(
        self,
        player_id: int,
        new_game_stats: dict[str, float],
        db_session: Session,
    ) -> PIQRating:
        """Full pipeline: gather history, compute subs, face cards, OVR, save.

        Parameters
        ----------
        player_id:
            Database id of the player.
        new_game_stats:
            Stats dict for the newly completed game.
        db_session:
            Active SQLAlchemy session for reads and writes.

        Returns
        -------
        The created or updated ``PIQRating`` ORM instance.
        """

        # 1. Gather game stats history (most recent first)
        game_stats_history = self._gather_game_history(player_id, db_session)
        game_stats_history.insert(0, new_game_stats)

        # 2. Look up player metadata
        from app.models.player import Player, POSITION_GROUP_MAP

        player = db_session.query(Player).filter(Player.id == player_id).first()
        if player is None:
            raise ValueError(f"Player {player_id} not found")

        position_group = POSITION_GROUP_MAP.get(
            player.position.value if player.position else "CM", "CM"
        )

        # Determine age group from team
        age_group = "U14"  # fallback
        if player.team and player.team.age_group:
            age_group = player.team.age_group.value

        # Determine competition tier
        competition_tier = 6  # default: Competitive Travel
        if player.team:
            competition_tier = player.team.competition_tier or 6

        # 3. Compute sub-attributes
        sub_attrs = self.compute_sub_attributes(game_stats_history, age_group)

        # 4. Compute face-card attributes
        face_cards = self.compute_face_card_attributes(sub_attrs)

        # 5. Compute OVR
        ovr = self.compute_ovr(face_cards, position_group)

        # 6. Apply competition tier multiplier
        from app.services.competition_tier import CompetitionTierService

        tier_service = CompetitionTierService()
        level_multiplier = tier_service.get_level_multiplier(competition_tier)

        # Tier adjustment: scale OVR toward global baseline
        # OVR is within a tier-local context; adjust proportionally
        adjusted_ovr = int(round(max(1, min(99, ovr * level_multiplier))))

        # Adjust face-card attributes similarly
        adjusted_face_cards = {
            k: int(round(max(1, min(99, v * level_multiplier))))
            for k, v in face_cards.items()
        }

        # Adjust sub-attributes
        adjusted_sub_attrs = {
            k: int(round(max(1, min(99, v * level_multiplier))))
            for k, v in sub_attrs.items()
        }

        # 7. Determine confidence level
        games_count = len(game_stats_history)
        confidence = self.get_confidence_level(games_count)

        # 8. Persist
        existing_rating: Optional[PIQRating] = (
            db_session.query(PIQRating)
            .filter(PIQRating.player_id == player_id)
            .first()
        )

        if existing_rating is None:
            rating = PIQRating(
                player_id=player_id,
                ovr=adjusted_ovr,
                spd=adjusted_face_cards.get("spd", 50),
                sht=adjusted_face_cards.get("sht", 50),
                pas=adjusted_face_cards.get("pas", 50),
                drb=adjusted_face_cards.get("drb", 50),
                _def=adjusted_face_cards.get("def", 50),
                phy=adjusted_face_cards.get("phy", 50),
                sub_attributes=adjusted_sub_attrs,
                competition_tier=competition_tier,
                level_multiplier_applied=level_multiplier,
                games_analyzed_count=games_count,
                confidence_level=confidence,
            )
            db_session.add(rating)
        else:
            rating = existing_rating
            rating.ovr = adjusted_ovr
            rating.spd = adjusted_face_cards.get("spd", 50)
            rating.sht = adjusted_face_cards.get("sht", 50)
            rating.pas = adjusted_face_cards.get("pas", 50)
            rating.drb = adjusted_face_cards.get("drb", 50)
            rating._def = adjusted_face_cards.get("def", 50)
            rating.phy = adjusted_face_cards.get("phy", 50)
            rating.sub_attributes = adjusted_sub_attrs
            rating.competition_tier = competition_tier
            rating.level_multiplier_applied = level_multiplier
            rating.games_analyzed_count = games_count
            rating.confidence_level = confidence

        db_session.flush()

        # 9. Create history snapshot
        # Determine the triggering game id
        latest_game_player = (
            db_session.query(GamePlayer)
            .filter(GamePlayer.player_id == player_id)
            .order_by(GamePlayer.id.desc())
            .first()
        )
        triggered_game_id = latest_game_player.game_id if latest_game_player else None

        history_entry = PIQRatingHistory(
            piq_rating_id=rating.id,
            player_id=player_id,
            ovr=adjusted_ovr,
            attributes={
                "face_cards": adjusted_face_cards,
                "sub_attributes": adjusted_sub_attrs,
            },
            games_analyzed_count=games_count,
            triggered_by_game_id=triggered_game_id,
            snapshot_date=date.today(),
        )
        db_session.add(history_entry)
        db_session.flush()

        logger.info(
            "Updated PIQ rating for player %d: OVR=%d (tier=%d, mult=%.2f, confidence=%s)",
            player_id, adjusted_ovr, competition_tier, level_multiplier, confidence.value,
        )
        return rating

    @staticmethod
    def get_confidence_level(games_count: int) -> PIQConfidenceLevel:
        """Map number of analysed games to a confidence level.

        Returns
        -------
        PIQConfidenceLevel enum value.
        """
        if games_count < 3:
            return PIQConfidenceLevel.CALCULATING
        elif games_count <= 5:
            return PIQConfidenceLevel.PRELIMINARY
        elif games_count <= 10:
            return PIQConfidenceLevel.DEVELOPING
        else:
            return PIQConfidenceLevel.ESTABLISHED

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _stat_to_percentile(
        raw_value: float,
        stat_name: str,
        benchmarks: dict[str, dict[str, float]],
    ) -> float:
        """Convert a single raw stat value to a 0-100 percentile.

        Inverse metrics are flipped so that a *lower* raw value yields a
        *higher* percentile.
        """
        bench = benchmarks.get(stat_name)
        if bench is None:
            return 50.0

        mean = bench["mean"]
        std = bench["std"]
        if std <= 0:
            std = 1.0

        z = (raw_value - mean) / std
        percentile = float(scipy_stats.norm.cdf(z) * 100.0)

        if stat_name in _INVERSE_STAT_METRICS:
            percentile = 100.0 - percentile

        return max(0.5, min(99.5, percentile))

    @staticmethod
    def _gather_game_history(
        player_id: int,
        db_session: Session,
    ) -> list[dict[str, float]]:
        """Load per-game stat dicts for a player, most recent first.

        Returns up to ``settings.piq_rolling_window`` games.
        """
        window = settings.piq_rolling_window

        # Join GamePlayer -> Game for ordering, then pivot PlayerGameStats
        game_players = (
            db_session.query(GamePlayer)
            .join(Game, Game.id == GamePlayer.game_id)
            .filter(GamePlayer.player_id == player_id)
            .order_by(Game.game_date.desc())
            .limit(window)
            .all()
        )

        history: list[dict[str, float]] = []
        for gp in game_players:
            stats_rows = (
                db_session.query(PlayerGameStats)
                .filter(PlayerGameStats.game_player_id == gp.id)
                .all()
            )
            game_dict: dict[str, float] = {}
            for row in stats_rows:
                game_dict[row.metric_name] = row.metric_value
            if game_dict:
                history.append(game_dict)

        return history
