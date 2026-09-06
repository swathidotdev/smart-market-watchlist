"""Combination weights, the surfacing threshold, and dominant-factor selection.

Imports nothing from the rest of the engine -- keeps the dependency graph acyclic
(scoring imports this, not the other way around).

WHY THESE NUMBERS: they are tuned so the ranking is significance, not raw size.
A stock that moves a lot *with the market* stays below threshold; a stock that
moves unusually *for itself* crosses it. test_change_engine.py asserts exactly
that contrast, so these constants are documented by their tests.
"""
from __future__ import annotations

# Volatility carries the most weight (is this move unusual for THIS stock),
# market-relative next (is it stock-specific or just the market), volume last
# (corroborating / early signal). Sums to 1.0 so a score reads as weighted-avg
# "sigma units of significance."
WEIGHTS: dict[str, float] = {
    "volatility": 0.40,
    "market": 0.35,
    "volume": 0.25,
}

# A combined score at or above this surfaces in the ranked feed.
SURFACING_THRESHOLD: float = 1.8


def combine(volatility: float, market: float, volume: float) -> float:
    return (
        WEIGHTS["volatility"] * volatility
        + WEIGHTS["market"] * market
        + WEIGHTS["volume"] * volume
    )


def dominant_factor(volatility: float, market: float, volume: float) -> str:
    """The component contributing most to the score -- drives the headline."""
    contributions = {
        "volatility": WEIGHTS["volatility"] * volatility,
        "market": WEIGHTS["market"] * market,
        "volume": WEIGHTS["volume"] * volume,
    }
    return max(contributions, key=lambda k: contributions[k])


def crosses_threshold(score: float) -> bool:
    return score >= SURFACING_THRESHOLD