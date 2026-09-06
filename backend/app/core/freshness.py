"""Freshness state machine: LIVE / RECENT / DELAYED / STALE / UNAVAILABLE.

A gate on TRUST, not a scoring dimension (ARCHITECTURE.md). The system must
never present stale data with the confidence of fresh data.

STALE = market closed (weekend/after-hours). It is an EXPECTED, calm state, not
degraded confidence. UNAVAILABLE = we have no data at all. DELAYED = market is
open but our data is older than it should be.

NSE regular session: 09:15-15:30 IST, Mon-Fri. Exchange holidays are out of
scope for now (a holiday reads as STALE, which is the correct calm state anyway).
`now` is injectable for testability.
"""
from __future__ import annotations

from datetime import datetime, time, timezone
from enum import Enum
from zoneinfo import ZoneInfo

IST = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9, 15)
MARKET_CLOSE = time(15, 30)

LIVE_MAX_AGE_S = 120       # <= 2 min
RECENT_MAX_AGE_S = 900     # <= 15 min
# older than RECENT while market is open -> DELAYED


class FreshnessState(str, Enum):
    LIVE = "LIVE"
    RECENT = "RECENT"
    DELAYED = "DELAYED"
    STALE = "STALE"
    UNAVAILABLE = "UNAVAILABLE"

    @property
    def label(self) -> str:
        # DESIGN.md: sentence case in the UI ("Delayed", not "DELAYED").
        return self.name.capitalize()


def is_market_open(now: datetime) -> bool:
    ist = now.astimezone(IST)
    if ist.weekday() >= 5:  # Sat / Sun
        return False
    return MARKET_OPEN <= ist.time() <= MARKET_CLOSE


def assess_freshness(
    fetched_at: datetime | None,
    now: datetime | None = None,
) -> FreshnessState:
    now = now or datetime.now(timezone.utc)

    if fetched_at is None:
        return FreshnessState.UNAVAILABLE

    if fetched_at.tzinfo is None:
        fetched_at = fetched_at.replace(tzinfo=timezone.utc)

    if not is_market_open(now):
        # Data can't be fresher than the last session -- expected, calm.
        return FreshnessState.STALE

    age = (now - fetched_at).total_seconds()
    if age <= LIVE_MAX_AGE_S:
        return FreshnessState.LIVE
    if age <= RECENT_MAX_AGE_S:
        return FreshnessState.RECENT
    return FreshnessState.DELAYED