"""LAST SEEN baseline resolution + UserCheck recording.

The LAST SEEN baseline is the timestamp of the user's most recent PRIOR DISTINCT
dashboard load -- per-user, not per-device (multiple devices share one baseline,
so switching devices doesn't manufacture a fake delta -- PRD section 6).

Rapid repeated loads are deduplicated within a short window, so a
near-simultaneous second load doesn't reset the baseline to "just now" and hide
what the first load surfaced.

decide_baseline is a PURE function (unit-tested without a DB). open_dashboard is
the thin DB wrapper that fetches the two most recent checks and applies it.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.user_check import UserCheck


@dataclass(frozen=True)
class BaselineDecision:
    baseline_at: datetime | None   # compare "since" this (None == first-time)
    should_record: bool            # is this load a distinct new check?


def decide_baseline(
    latest: datetime | None,
    prev: datetime | None,
    now: datetime,
    dedup_window_s: int,
) -> BaselineDecision:
    """Pure baseline decision.

    - No prior check          -> first time: baseline None, record.
    - latest within window    -> near-simultaneous repeat: baseline is the check
                                 BEFORE latest (prev), do NOT record a duplicate.
    - latest older than window -> genuine new session: baseline is latest, record.
    """
    if latest is None:
        return BaselineDecision(baseline_at=None, should_record=True)

    age = (now - latest).total_seconds()
    if age < dedup_window_s:
        return BaselineDecision(baseline_at=prev, should_record=False)

    return BaselineDecision(baseline_at=latest, should_record=True)


async def _two_most_recent(
    db: AsyncSession, user_id: int
) -> tuple[datetime | None, datetime | None]:
    rows = (
        await db.execute(
            select(UserCheck.checked_at)
            .where(UserCheck.user_id == user_id)
            .order_by(UserCheck.checked_at.desc())
            .limit(2)
        )
    ).scalars().all()
    latest = rows[0] if len(rows) >= 1 else None
    prev = rows[1] if len(rows) >= 2 else None
    return latest, prev


async def open_dashboard(
    db: AsyncSession, user_id: int, now: datetime | None = None
) -> datetime | None:
    """Resolve the LAST SEEN baseline for a dashboard load and record the check
    (deduplicated). Returns the baseline timestamp (None for first-time).

    `now` is injectable for deterministic scripts/tests.
    """
    now = now or datetime.now(timezone.utc)
    latest, prev = await _two_most_recent(db, user_id)
    decision = decide_baseline(latest, prev, now, settings.check_dedup_window_seconds)
    if decision.should_record:
        db.add(UserCheck(user_id=user_id, checked_at=now))
        await db.commit()
    return decision.baseline_at