"""Manual Phase-E check. Requires the DB migrated (alembic upgrade head).

Two scenarios, per PHASES.md:
  1. Baseline: several loads with injected timestamps -> baseline resolves against
     the right prior check; a rapid repeat does not reset it.
  2. Acknowledgment: a change surfaces, is acknowledged, does NOT re-surface on
     reload, but a genuinely new session DOES -- and ack is per-symbol.

Run from backend/:  python -m scripts.last_check_check
"""
import asyncio
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import delete, select

from app.core.last_check.acknowledgment import (
    acknowledge_symbol,
    get_unacknowledged_events,
    record_change_event,
    unacknowledged_symbols,
)
from app.core.last_check.baseline import open_dashboard
from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.change_event import ChangeEvent
from app.models.user import User
from app.models.user_check import UserCheck

EMAIL = "lastcheck@test.local"
UTC = timezone.utc


async def _fresh_user() -> int:
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = User(email=EMAIL, password_hash=hash_password("password123"))
            db.add(user)
            await db.flush()
        # clean slate for repeatable runs
        await db.execute(delete(ChangeEvent).where(ChangeEvent.user_id == user.id))
        await db.execute(delete(UserCheck).where(UserCheck.user_id == user.id))
        await db.commit()
        return user.id


async def scenario_baseline(user_id: int) -> None:
    print("=== Scenario 1: baseline resolution ===")
    base = datetime(2025, 3, 1, 9, 0, tzinfo=UTC)

    async def load(now, label):
        async with SessionLocal() as db:
            b = await open_dashboard(db, user_id, now=now)
        print(f"  {label:28} now={now.time()} -> baseline={b}")
        return b

    b1 = await load(base, "first load")
    assert b1 is None, "first load should be first-time (None)"

    b2 = await load(base + timedelta(hours=1), "new session (+1h)")
    assert b2 == base, "should compare against the first load"

    b3 = await load(base + timedelta(hours=1, seconds=5), "rapid repeat (+5s)")
    assert b3 == base, "rapid repeat must NOT reset baseline to +1h"

    b4 = await load(base + timedelta(hours=3), "new session (+3h)")
    assert b4 == base + timedelta(hours=1), "should compare against the +1h check"

    print("  OK: baseline resolves correctly and dedup does not reset it.\n")


async def scenario_acknowledgment(user_id: int) -> None:
    print("=== Scenario 2: acknowledgment ===")
    d1, d2 = date(2025, 3, 10), date(2025, 3, 11)

    async def record(symbol, event_date, score):
        async with SessionLocal() as db:
            await record_change_event(
                db, user_id=user_id, symbol=symbol, exchange="NSE",
                event_date=event_date, score=score,
                dominant_factor="volatility",
                explanation=f"{score:.1f}x this stock's normal daily swing",
            )

    async def pending():
        async with SessionLocal() as db:
            return await unacknowledged_symbols(db, user_id)

    # RELIANCE and TCS both surface a change on d1
    await record("RELIANCE", d1, 2.5)
    await record("TCS", d1, 2.1)
    print(f"  after surfacing d1 changes, pending = {sorted(await pending())}")
    assert await pending() == {"RELIANCE", "TCS"}

    # Acknowledge only RELIANCE
    async with SessionLocal() as db:
        n = await acknowledge_symbol(db, user_id, "RELIANCE", "NSE")
    print(f"  acknowledged RELIANCE ({n} event(s)); pending = {sorted(await pending())}")
    assert await pending() == {"TCS"}, "ack should be per-symbol"

    # Reload recomputes the SAME d1 session for RELIANCE -> must NOT resurface
    await record("RELIANCE", d1, 2.5)
    print(f"  after reload of d1, pending = {sorted(await pending())}")
    assert await pending() == {"TCS"}, "acknowledged change must not re-surface"

    # A genuinely new session d2 for RELIANCE -> DOES surface again
    await record("RELIANCE", d2, 2.7)
    print(f"  after new session d2, pending = {sorted(await pending())}")
    assert await pending() == {"RELIANCE", "TCS"}, "a new session should surface"

    async with SessionLocal() as db:
        evs = await get_unacknowledged_events(db, user_id)
    print("  pending events:", [(e.symbol, str(e.event_date), e.score) for e in evs])
    print("  OK: ack is per-symbol; acked sessions stay quiet; new sessions surface.\n")


async def main() -> None:
    user_id = await _fresh_user()
    await scenario_baseline(user_id)
    await scenario_acknowledgment(user_id)
    print("Phase E scenarios passed.")


if __name__ == "__main__":
    asyncio.run(main())