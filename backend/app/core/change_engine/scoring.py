"""The three explainable components + combined score for ONE session.

Every number here is hand-checkable -- that is why test_change_engine.py can
assert exact values rather than snapshots.

Components (PRD section 5), all measured against this stock's OWN recent normal:
  volatility : |today's return| / pstdev(trailing daily returns)     -> sigma units
  market     : |today's excess| / pstdev(trailing excess returns)    -> sigma units
               excess = stock return - Nifty 50 return
  volume     : today's volume / mean(trailing volume, excluding today) -> a ratio

Volatility and market are in sigma units (how many std devs from normal).
Volume contributes as max(0, ratio - 1): only ELEVATED volume is a signal --
low volume is not an event (deliberate, documented asymmetry).

Never raises on missing/short data: returns STATUS_INSUFFICIENT instead
(RULES.md -- a first-time symbol or a gap is expected, not exceptional).
"""
from __future__ import annotations

import statistics
from dataclasses import dataclass
from datetime import date

from app.core.change_engine import thresholds
from app.data_providers.base import Bar

# --- tuning constants (core IP; asserted by tests) ---
TRAILING_WINDOW = 20      # sessions of history used for "normal"
MIN_HISTORY = 10          # fewer trailing returns than this -> insufficient
MIN_EXCESS = 5            # fewer aligned excess returns than this -> skip market
COMPONENT_CAP = 10.0      # bound a component when sigma is ~0 (flat baseline)

FACTOR_VOLATILITY = "volatility"
FACTOR_MARKET = "market"
FACTOR_VOLUME = "volume"

STATUS_OK = "ok"
STATUS_INSUFFICIENT = "insufficient_data"


@dataclass(frozen=True)
class ComponentScores:
    # normalized (used for scoring)
    volatility: float
    market: float
    volume: float
    # raw display values (used for explanations / detail view)
    return_pct: float          # today's return, in %
    volatility_ratio: float    # "Nx normal swing"
    market_excess_pp: float    # signed pp vs Nifty (+ above, - below)
    volume_ratio: float        # "Nx normal volume"


@dataclass(frozen=True)
class ScoreResult:
    obs_date: date | None
    status: str
    score: float
    dominant_factor: str
    direction: int             # +1 up, -1 down, 0 flat
    components: ComponentScores | None


# --- small helpers ---------------------------------------------------------

def _stock_return(closes: list[float], j: int) -> float:
    prev = closes[j - 1]
    return (closes[j] - prev) / prev if prev else 0.0


def _bench_return(stock_bars: list[Bar], j: int, bench_by_date: dict) -> float | None:
    """Benchmark return aligned to the stock's own trading dates."""
    b = bench_by_date.get(stock_bars[j].date)
    bp = bench_by_date.get(stock_bars[j - 1].date)
    if b is None or bp is None or bp.close == 0:
        return None
    return (b.close - bp.close) / bp.close


def _ratio_over_sigma(value: float, sigma: float) -> float:
    """|value| / sigma, capped. Flat baseline (sigma ~ 0): any move -> cap, none -> 0."""
    if sigma <= 0.0:
        return COMPONENT_CAP if abs(value) > 0 else 0.0
    return min(abs(value) / sigma, COMPONENT_CAP)


# --- the scorer ------------------------------------------------------------

def score_session(
    stock_bars: list[Bar],
    benchmark_bars: list[Bar],
    target_date: date | None = None,
) -> ScoreResult:
    if not stock_bars:
        return ScoreResult(None, STATUS_INSUFFICIENT, 0.0, "", 0, None)

    # locate the session to score
    if target_date is None:
        t = len(stock_bars) - 1
    else:
        t = next((i for i, b in enumerate(stock_bars) if b.date == target_date), -1)
    if t < 1:
        d = stock_bars[t].date if 0 <= t < len(stock_bars) else target_date
        return ScoreResult(d, STATUS_INSUFFICIENT, 0.0, "", 0, None)

    closes = [b.close for b in stock_bars]
    volumes = [b.volume for b in stock_bars]
    start = max(1, t - TRAILING_WINDOW)  # window = indices [start .. t-1]

    trailing_returns = [_stock_return(closes, j) for j in range(start, t)]
    if len(trailing_returns) < MIN_HISTORY:
        return ScoreResult(stock_bars[t].date, STATUS_INSUFFICIENT, 0.0, "", 0, None)

    r_today = _stock_return(closes, t)

    # 1. volatility-relative
    sigma_r = statistics.pstdev(trailing_returns)
    volatility = _ratio_over_sigma(r_today, sigma_r)

    # 2. market-relative
    bench_by_date = {b.date: b for b in benchmark_bars}
    bench_today = _bench_return(stock_bars, t, bench_by_date)
    trailing_excess = []
    for j in range(start, t):
        br = _bench_return(stock_bars, j, bench_by_date)
        if br is not None:
            trailing_excess.append(_stock_return(closes, j) - br)

    if bench_today is None or len(trailing_excess) < MIN_EXCESS:
        market = 0.0
        market_excess_pp = 0.0
    else:
        excess_today = r_today - bench_today
        sigma_excess = statistics.pstdev(trailing_excess)
        market = _ratio_over_sigma(excess_today, sigma_excess)
        market_excess_pp = excess_today * 100.0

    # 3. volume anomaly
    trailing_vols = volumes[start:t]  # excludes today (index t)
    mean_vol = statistics.mean(trailing_vols) if trailing_vols else 0.0
    if mean_vol > 0:
        volume_ratio = volumes[t] / mean_vol
        volume = max(0.0, volume_ratio - 1.0)
    else:
        volume_ratio = 0.0
        volume = 0.0

    score = thresholds.combine(volatility, market, volume)
    dominant = thresholds.dominant_factor(volatility, market, volume)
    direction = 1 if r_today > 0 else (-1 if r_today < 0 else 0)

    components = ComponentScores(
        volatility=volatility,
        market=market,
        volume=volume,
        return_pct=r_today * 100.0,
        volatility_ratio=volatility,   # == |r|/sigma (capped); display value
        market_excess_pp=market_excess_pp,
        volume_ratio=volume_ratio,
    )
    return ScoreResult(stock_bars[t].date, STATUS_OK, score, dominant, direction, components)