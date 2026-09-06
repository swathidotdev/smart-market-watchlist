"""The core-IP test suite. Fixtures are HAND-COMPUTABLE: a trailing window of
alternating +/-1% returns has population stddev exactly 0.01, so |return|/sigma
and excess/sigma come out to round numbers we assert directly. The arithmetic is
written in the comments -- this file is both the proof and the documentation.
"""
from datetime import date, timedelta

import pytest

from app.core.change_engine import evaluate_change
from app.core.change_engine.explanations import explain
from app.core.change_engine.peak_detection import find_peak_event
from app.core.change_engine.scoring import (
    FACTOR_MARKET,
    FACTOR_VOLATILITY,
    FACTOR_VOLUME,
    STATUS_INSUFFICIENT,
    STATUS_OK,
    score_session,
)
from app.core.change_engine.thresholds import crosses_threshold
from app.data_providers.base import Bar

# 20 alternating +/-1% returns: mean 0, population stddev exactly 0.01.
WINDOW = [0.01 if i % 2 == 0 else -0.01 for i in range(20)]


def _dates(n: int, start=date(2025, 1, 1)):
    return [start + timedelta(days=i) for i in range(n)]


def _series(returns_after_first, volumes, start_close=100.0):
    """Build Bars. len(volumes) must equal len(returns_after_first) + 1."""
    closes = [start_close]
    for r in returns_after_first:
        closes.append(closes[-1] * (1 + r))
    ds = _dates(len(closes))
    return [
        Bar(date=d, open=c, high=c, low=c, close=c, volume=v)
        for d, c, v in zip(ds, closes, volumes)
    ]


# ---------------------------------------------------------------------------
# 1. Anomaly: the hero case. All arithmetic spelled out.
# ---------------------------------------------------------------------------
def test_anomaly_scores_and_flags_with_exact_math():
    # target return +3.1%; window sigma 0.01 -> volatility = 0.031/0.01 = 3.1
    stock = _series(WINDOW + [0.031], [1_000_000] * 21 + [2_200_000])
    # benchmark flat in window, +1% on target day
    bench = _series([0.0] * 20 + [0.01], [0] * 22, start_close=20_000.0)

    r = score_session(stock, bench)
    assert r.status == STATUS_OK
    c = r.components

    # volatility: |0.031| / 0.01 = 3.1
    assert c.volatility_ratio == pytest.approx(3.1)
    # market: excess = 0.031 - 0.01 = 0.021; sigma_excess = 0.01 -> 2.1 ; pp = 2.1
    assert c.market == pytest.approx(2.1)
    assert c.market_excess_pp == pytest.approx(2.1)
    # volume: 2.2M / 1.0M = 2.2
    assert c.volume_ratio == pytest.approx(2.2)
    # score = 0.40*3.1 + 0.35*2.1 + 0.25*(2.2-1) = 1.24 + 0.735 + 0.30 = 2.275
    assert r.score == pytest.approx(2.275)
    assert r.dominant_factor == FACTOR_VOLATILITY
    assert r.direction == 1
    assert crosses_threshold(r.score) is True
    assert explain(r) == "3.1x this stock's normal daily swing"


# ---------------------------------------------------------------------------
# 2. Contrast beat as a unit test: big move, but market-tracking -> NOT flagged.
# ---------------------------------------------------------------------------
def test_market_tracking_big_mover_does_not_flag():
    stock = _series(WINDOW + [0.030], [1_000_000] * 22)      # +3.0% move
    bench = _series([0.0] * 20 + [0.028], [0] * 22, start_close=20_000.0)  # market +2.8%

    r = score_session(stock, bench)
    # volatility 3.0 (a BIG move for the stock) ...
    assert r.components.volatility_ratio == pytest.approx(3.0)
    # ... but excess = 0.002 -> market 0.2, volume 0
    # score = 0.40*3.0 + 0.35*0.2 + 0 = 1.2 + 0.07 = 1.27
    assert r.score == pytest.approx(1.27)
    assert crosses_threshold(r.score) is False   # moved a lot, still not flagged


# ---------------------------------------------------------------------------
# 3. Quiet day: nothing meaningful.
# ---------------------------------------------------------------------------
def test_quiet_day_below_threshold():
    stock = _series(WINDOW + [0.008], [1_000_000] * 22)
    bench = _series([0.0] * 20 + [0.007], [0] * 22, start_close=20_000.0)

    r = score_session(stock, bench)
    # score = 0.40*0.8 + 0.35*0.1 + 0 = 0.355
    assert r.score == pytest.approx(0.355)
    assert crosses_threshold(r.score) is False


# ---------------------------------------------------------------------------
# 4. Never crashes on short history.
# ---------------------------------------------------------------------------
def test_insufficient_history_is_a_state_not_a_crash():
    stock = _series([0.01] * 5, [1_000_000] * 6)   # only 5 trailing returns
    bench = _series([0.0] * 5, [0] * 6, start_close=20_000.0)
    r = score_session(stock, bench)
    assert r.status == STATUS_INSUFFICIENT
    assert explain(r) == "Not enough history yet to assess this."


# ---------------------------------------------------------------------------
# 5. Peak detection across a gap: a whipsaw that looks flat end-to-end.
# ---------------------------------------------------------------------------
def test_peak_detection_catches_whipsaw_not_endpoint_diff():
    # ... normal window, then drop -3.1%, then recover +3.2%
    stock = _series(WINDOW + [-0.031, 0.032], [1_000_000] * 23)
    bench = _series([0.0] * 22, [0] * 23, start_close=20_000.0)

    baseline = stock[20].date  # last check was just before the whipsaw
    peak = find_peak_event(stock, bench, baseline_date=baseline)

    # The peak is the DROP day, and it's clearly significant...
    assert peak.obs_date == stock[21].date
    assert peak.direction == -1
    assert crosses_threshold(peak.score) is True

    # ... even though a naive endpoint diff over the gap looks ~flat.
    net = (stock[22].close - stock[20].close) / stock[20].close
    assert abs(net) < 0.005

    # Drop day out-scores the recovery day (recovery's window is noisier).
    drop = score_session(stock, bench, stock[21].date)
    recovery = score_session(stock, bench, stock[22].date)
    assert drop.score > recovery.score


def test_no_new_session_since_baseline_is_no_change():
    stock = _series(WINDOW + [0.031], [1_000_000] * 22)
    bench = _series([0.0] * 21, [0] * 22, start_close=20_000.0)
    latest = stock[-1].date
    r = find_peak_event(stock, bench, baseline_date=latest)  # baseline == latest
    assert r.status == STATUS_OK
    assert r.score == 0.0            # nothing new happened
    assert crosses_threshold(r.score) is False


# ---------------------------------------------------------------------------
# 6. Explanations for the other two dominant factors.
# ---------------------------------------------------------------------------
def test_volume_dominant_explanation_flat_price():
    stock = _series(WINDOW + [0.002], [1_000_000] * 21 + [2_600_000])  # tiny move
    bench = _series([0.0] * 20 + [0.001], [0] * 22, start_close=20_000.0)
    r = score_session(stock, bench)
    assert r.dominant_factor == FACTOR_VOLUME
    assert explain(r) == "Volume 2.6x normal -- unusual given a flat price"


def test_market_dominant_explanation():
    # small stock move (+0.5%), but market dropped -2% -> big positive excess
    stock = _series(WINDOW + [0.005], [1_000_000] * 22)
    bench = _series([0.0] * 20 + [-0.020], [0] * 22, start_close=20_000.0)
    r = score_session(stock, bench)
    # excess = 0.005 - (-0.020) = 0.025 -> market 2.5 ; volatility 0.5
    assert r.dominant_factor == FACTOR_MARKET
    assert explain(r) == "2.5pp above the Nifty 50"


# ---------------------------------------------------------------------------
# 7. evaluate_change ties it together.
# ---------------------------------------------------------------------------
def test_evaluate_change_end_to_end():
    stock = _series(WINDOW + [0.031], [1_000_000] * 21 + [2_200_000])
    bench = _series([0.0] * 20 + [0.01], [0] * 22, start_close=20_000.0)
    ev = evaluate_change(stock, bench, baseline_date=stock[20].date)
    assert ev.crosses_threshold is True
    assert ev.result.dominant_factor == FACTOR_VOLATILITY
    assert ev.explanation == "3.1x this stock's normal daily swing"