"""Pure baseline-decision tests. No DB -- decide_baseline is deliberately pure so
the tricky dedup semantics are provable in isolation.
"""
from datetime import datetime, timedelta, timezone

from app.core.last_check.baseline import decide_baseline

UTC = timezone.utc
T0 = datetime(2025, 1, 1, 10, 0, tzinfo=UTC)


def test_first_time_user_no_baseline_records():
    d = decide_baseline(latest=None, prev=None, now=T0, dedup_window_s=30)
    assert d.baseline_at is None
    assert d.should_record is True


def test_genuine_new_session_compares_against_latest():
    now = T0 + timedelta(hours=1)
    d = decide_baseline(latest=T0, prev=None, now=now, dedup_window_s=30)
    assert d.baseline_at == T0
    assert d.should_record is True


def test_rapid_repeat_first_time_stays_first_time():
    now = T0 + timedelta(seconds=5)  # within window
    d = decide_baseline(latest=T0, prev=None, now=now, dedup_window_s=30)
    assert d.baseline_at is None       # prev is None -> still first-time-ish
    assert d.should_record is False    # no duplicate row


def test_rapid_repeat_uses_prev_not_latest_as_baseline():
    prev, latest = T0, T0 + timedelta(hours=1)
    now = latest + timedelta(seconds=5)
    d = decide_baseline(latest=latest, prev=prev, now=now, dedup_window_s=30)
    # baseline is prev, NOT latest -> the first load's changes stay visible
    assert d.baseline_at == prev
    assert d.should_record is False


def test_new_session_after_a_deduped_pair():
    prev, latest = T0, T0 + timedelta(hours=1)
    now = latest + timedelta(hours=2)
    d = decide_baseline(latest=latest, prev=prev, now=now, dedup_window_s=30)
    assert d.baseline_at == latest
    assert d.should_record is True


def test_window_boundary_is_exclusive_lower():
    # exactly at the window edge counts as a new session (age == window is not < window)
    now = T0 + timedelta(seconds=30)
    d = decide_baseline(latest=T0, prev=None, now=now, dedup_window_s=30)
    assert d.should_record is True
    assert d.baseline_at == T0