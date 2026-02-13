"""Competition tier and level multiplier service for PitchIQ.

Defines the 8-tier US youth soccer competition hierarchy and provides
methods for applying tier-based multipliers to PIQ ratings, simulating
tier changes, and assessing promotion readiness.
"""

from __future__ import annotations

import copy
import logging
from typing import Any, Optional

from app.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tier configuration
# ---------------------------------------------------------------------------

TIER_CONFIG: dict[int, dict[str, Any]] = {
    1: {
        "name": "Elite (MLS NEXT/ECNL)",
        "multiplier": 1.00,
        "examples_boys": "MLS NEXT (MLS Academy)",
        "examples_girls": "ECNL",
    },
    2: {
        "name": "National (GA/MLS NEXT)",
        "multiplier": 0.95,
        "examples_boys": "MLS NEXT (non-MLS)",
        "examples_girls": "Girls Academy",
    },
    3: {
        "name": "High National (ECRL/DPL)",
        "multiplier": 0.88,
        "examples_boys": "ECRL, NAL",
        "examples_girls": "GA Aspire, DPL",
    },
    4: {
        "name": "National/Regional (NPL)",
        "multiplier": 0.80,
        "examples_boys": "NPL, USYS NL",
        "examples_girls": "NPL Girls, USYS NL",
    },
    5: {
        "name": "State Premier",
        "multiplier": 0.72,
        "examples_boys": "State Premier League",
        "examples_girls": "State Premier / Div 1",
    },
    6: {
        "name": "Competitive Travel",
        "multiplier": 0.62,
        "examples_boys": "Club travel",
        "examples_girls": "Club travel",
    },
    7: {
        "name": "Recreational+",
        "multiplier": 0.50,
        "examples_boys": "Advanced rec, town travel",
        "examples_girls": "Advanced rec",
    },
    8: {
        "name": "Recreational",
        "multiplier": 0.40,
        "examples_boys": "Rec leagues",
        "examples_girls": "Rec leagues",
    },
}


class CompetitionTierService:
    """Provides tier-aware adjustments for PIQ ratings."""

    # ------------------------------------------------------------------
    # Basic lookups
    # ------------------------------------------------------------------

    @staticmethod
    def get_level_multiplier(tier: int) -> float:
        """Return the level multiplier for a given tier (1-8).

        Defaults to 0.62 (Tier 6 -- Competitive Travel) if the tier is
        unrecognised.
        """
        config = TIER_CONFIG.get(tier)
        if config is None:
            logger.warning("Unknown competition tier %d; defaulting to Tier 6 multiplier", tier)
            return TIER_CONFIG[6]["multiplier"]
        return config["multiplier"]

    @staticmethod
    def get_tier_name(tier: int) -> str:
        """Return the human-readable name of a tier."""
        config = TIER_CONFIG.get(tier)
        if config is None:
            return "Unknown Tier"
        return config["name"]

    @staticmethod
    def get_tier_info(tier: int) -> dict[str, Any]:
        """Return the full tier config dict including name, multiplier, and examples.

        Returns an empty dict if the tier is not found.
        """
        config = TIER_CONFIG.get(tier)
        if config is None:
            return {}
        # Return a copy so callers cannot mutate the shared config
        result = copy.deepcopy(config)
        result["tier"] = tier
        return result

    @staticmethod
    def get_all_tiers() -> list[dict[str, Any]]:
        """Return a list of all tier configs, ordered from Tier 1 to 8.

        Suitable for populating a UI dropdown.
        """
        tiers: list[dict[str, Any]] = []
        for tier_num in sorted(TIER_CONFIG.keys()):
            entry = copy.deepcopy(TIER_CONFIG[tier_num])
            entry["tier"] = tier_num
            tiers.append(entry)
        return tiers

    # ------------------------------------------------------------------
    # Percentile adjustment
    # ------------------------------------------------------------------

    @staticmethod
    def compute_global_percentile(
        local_percentile: float,
        tier: int,
    ) -> float:
        """Adjust a tier-local percentile to a global (cross-tier) percentile.

        Formula::

            tier_floor = multiplier * 10
            global_percentile = local_percentile * level_multiplier
                                + tier_floor * (1 - local_percentile / 100)

        This ensures that even a low-percentile player in a high tier still
        maps to a reasonable global percentile, while top-percentile players
        in lower tiers are capped by their tier's ceiling.

        Parameters
        ----------
        local_percentile:
            The player's percentile within their tier / league (0-100).
        tier:
            The competition tier number (1-8).

        Returns
        -------
        Adjusted global percentile (0-100), clamped.
        """
        config = TIER_CONFIG.get(tier)
        if config is None:
            logger.warning("Unknown tier %d in compute_global_percentile; using Tier 6", tier)
            config = TIER_CONFIG[6]

        level_multiplier = config["multiplier"]
        tier_floor = level_multiplier * 10.0

        global_pct = (
            local_percentile * level_multiplier
            + tier_floor * (1.0 - local_percentile / 100.0)
        )
        return max(0.0, min(100.0, global_pct))

    # ------------------------------------------------------------------
    # Tier simulation & promotion readiness
    # ------------------------------------------------------------------

    def simulate_tier_change(
        self,
        current_ovr: int,
        current_tier: int,
        target_tier: int,
        attributes: dict[str, int],
    ) -> dict[str, Any]:
        """Estimate OVR and attributes if the player moved to a different tier.

        This is a *projection* -- it rescales existing values using the ratio
        of multipliers.  It does not re-derive stats from scratch.

        Parameters
        ----------
        current_ovr:
            The player's current OVR (already tier-adjusted).
        current_tier:
            The tier the current OVR was computed at.
        target_tier:
            The tier to project into.
        attributes:
            Dict of face-card attribute name -> current value (1-99),
            already tier-adjusted.

        Returns
        -------
        Dict with keys ``"estimated_ovr"``, ``"estimated_attributes"``,
        ``"current_tier"``, ``"target_tier"``, ``"multiplier_ratio"``.
        """
        current_mult = self.get_level_multiplier(current_tier)
        target_mult = self.get_level_multiplier(target_tier)

        if current_mult == 0:
            current_mult = 0.01  # guard

        ratio = target_mult / current_mult

        estimated_ovr = int(round(max(1, min(99, current_ovr * ratio))))
        estimated_attrs = {
            k: int(round(max(1, min(99, v * ratio))))
            for k, v in attributes.items()
        }

        return {
            "estimated_ovr": estimated_ovr,
            "estimated_attributes": estimated_attrs,
            "current_tier": current_tier,
            "target_tier": target_tier,
            "multiplier_ratio": round(ratio, 4),
        }

    def get_promotion_readiness(
        self,
        player_attributes: dict[str, int],
        current_tier: int,
        target_tier: int,
    ) -> dict[str, Any]:
        """Assess whether a player is ready to compete at a higher tier.

        Compares the player's current (tier-adjusted) attributes against
        the *median* (50) at the target tier.  A player is considered
        "ready" if their projected attributes at the target tier are
        all >= a readiness threshold (default 40).

        Parameters
        ----------
        player_attributes:
            Dict of face-card attribute name -> current value (already
            tier-adjusted).
        current_tier:
            The player's current tier.
        target_tier:
            The tier being considered for promotion.

        Returns
        -------
        Dict with:
          - ``"ready"`` (bool): overall readiness verdict
          - ``"gap"`` (dict): per-attribute gap (negative = shortfall)
          - ``"projected_attributes"``: what the attributes would look like
          - ``"readiness_threshold"``: the threshold used
          - ``"current_tier"`` / ``"target_tier"``
        """
        readiness_threshold = 40  # minimum projected attribute to be "ready"

        current_mult = self.get_level_multiplier(current_tier)
        target_mult = self.get_level_multiplier(target_tier)

        if current_mult == 0:
            current_mult = 0.01

        ratio = target_mult / current_mult

        projected: dict[str, int] = {}
        gap: dict[str, int] = {}
        all_ready = True

        for attr_name, attr_value in player_attributes.items():
            proj = int(round(max(1, min(99, attr_value * ratio))))
            projected[attr_name] = proj
            attr_gap = proj - readiness_threshold
            gap[attr_name] = attr_gap
            if proj < readiness_threshold:
                all_ready = False

        return {
            "ready": all_ready,
            "gap": gap,
            "projected_attributes": projected,
            "readiness_threshold": readiness_threshold,
            "current_tier": current_tier,
            "target_tier": target_tier,
        }
