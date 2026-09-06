"""Change Intelligence Engine -- the product's core IP.

Pure logic: Bar lists in, scores/explanations out. No HTTP, no DB session, no
LLM (RULES.md hard boundary). Composed by the API layer in Phase F.

This __init__ re-exports the pieces and provides evaluate_change(), the one-call
orchestration used by the API and the tests.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.change_engine import explanations, peak_detection, scoring, thresholds
from app.core.change_engine.scoring import (
    ComponentScores,
    ScoreResult,
    score_session,
)
from app.core.change_engine.thresholds import SURFACING_THRESHOLD


@dataclass(frozen=True)
class ChangeEvaluation:
    """Everything the API needs for one symbol, in one object."""

    result: ScoreResult
    crosses_threshold: bool
    explanation: str


def evaluate_change(stock_bars, benchmark_bars, baseline_date=None) -> ChangeEvaluation:
    """Find the peak event since baseline, decide if it surfaces, explain it."""
    result = peak_detection.find_peak_event(stock_bars, benchmark_bars, baseline_date)
    crosses = (
        result.status == scoring.STATUS_OK
        and thresholds.crosses_threshold(result.score)
    )
    return ChangeEvaluation(
        result=result,
        crosses_threshold=crosses,
        explanation=explanations.explain(result),
    )


__all__ = [
    "ComponentScores",
    "ScoreResult",
    "ChangeEvaluation",
    "evaluate_change",
    "score_session",
    "SURFACING_THRESHOLD",
]