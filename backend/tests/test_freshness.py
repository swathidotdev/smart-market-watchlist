from datetime import datetime, timedelta

from app.core.freshness import IST, FreshnessState, assess_freshness, is_market_open

# 2025-01-08 is a Wednesday; 2025-01-11 is a Saturday.
WED_10AM_IST = datetime(2025, 1, 8, 10, 0, tzinfo=IST)
SAT_10AM_IST = datetime(2025, 1, 11, 10, 0, tzinfo=IST)


def test_market_hours():
    assert is_market_open(WED_10AM_IST) is True
    assert is_market_open(SAT_10AM_IST) is False
    assert is_market_open(datetime(2025, 1, 8, 8, 0, tzinfo=IST)) is False   # pre-open
    assert is_market_open(datetime(2025, 1, 8, 16, 0, tzinfo=IST)) is False  # post-close


def test_no_data_is_unavailable():
    assert assess_freshness(None, now=WED_10AM_IST) == FreshnessState.UNAVAILABLE


def test_market_open_age_buckets():
    now = WED_10AM_IST
    assert assess_freshness(now - timedelta(seconds=30), now=now) == FreshnessState.LIVE
    assert assess_freshness(now - timedelta(minutes=10), now=now) == FreshnessState.RECENT
    assert assess_freshness(now - timedelta(minutes=45), now=now) == FreshnessState.DELAYED


def test_market_closed_is_stale_regardless_of_age():
    # Fresh fetch but market shut -> STALE (calm, expected), never LIVE.
    assert assess_freshness(SAT_10AM_IST - timedelta(seconds=10), now=SAT_10AM_IST) == FreshnessState.STALE


def test_label_is_sentence_case():
    assert FreshnessState.DELAYED.label == "Delayed"
    assert FreshnessState.STALE.label == "Stale"