"""Templated, formula-driven plain-language explanations.

Hard boundary (RULES.md rule 4): NO model call, ever. Making the explanation
"smarter" means improving these templates, not prompting an LLM. This is what
keeps the system explainable rather than a black box.
"""
from __future__ import annotations

from app.core.change_engine.scoring import (
    FACTOR_MARKET,
    FACTOR_VOLATILITY,
    FACTOR_VOLUME,
    STATUS_OK,
    ScoreResult,
)


def explain(result: ScoreResult) -> str:
    if result.status != STATUS_OK:
        return "Not enough history yet to assess this."
    if result.components is None:
        return "No meaningful change."

    c = result.components

    if result.dominant_factor == FACTOR_VOLATILITY:
        return f"{c.volatility_ratio:.1f}x this stock's normal daily swing"

    if result.dominant_factor == FACTOR_MARKET:
        direction = "above" if c.market_excess_pp >= 0 else "below"
        return f"{abs(c.market_excess_pp):.1f}pp {direction} the Nifty 50"

    if result.dominant_factor == FACTOR_VOLUME:
        base = f"Volume {c.volume_ratio:.1f}x normal"
        if c.volatility_ratio < 1.0:
            return f"{base} -- unusual given a flat price"
        return base

    return "No meaningful change."