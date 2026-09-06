"""Multi-day gap handling: scan intermediate sessions for the LARGEST event,
never naive-diff the two endpoints (PRD section 6).

A stock that dropped sharply and recovered between checks looks flat end-to-end
but is NOT a non-event -- this is what catches it.
"""
from __future__ import annotations

from datetime import date

from app.core.change_engine.scoring import STATUS_INSUFFICIENT, STATUS_OK, ScoreResult, score_session
from app.data_providers.base import Bar


def find_peak_event(
    stock_bars: list[Bar],
    benchmark_bars: list[Bar],
    baseline_date: date | None = None,
) -> ScoreResult:
    if not stock_bars:
        return ScoreResult(None, STATUS_INSUFFICIENT, 0.0, "", 0, None)

    if baseline_date is None:
        # First-time user: no baseline -> just assess the latest session.
        candidates = [stock_bars[-1].date]
    else:
        candidates = [b.date for b in stock_bars if b.date > baseline_date]
        if not candidates:
            # No new session since last check -> nothing new happened.
            return ScoreResult(stock_bars[-1].date, STATUS_OK, 0.0, "", 0, None)

    best: ScoreResult | None = None
    for d in candidates:
        r = score_session(stock_bars, benchmark_bars, d)
        if r.status != STATUS_OK:
            continue
        if best is None or r.score > best.score:
            best = r

    if best is None:  # every candidate was insufficient
        return score_session(stock_bars, benchmark_bars, candidates[-1])
    return best