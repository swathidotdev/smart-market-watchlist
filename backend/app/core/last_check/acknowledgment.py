"""ChangeEvent persistence + per-symbol acknowledgment.

Acknowledgment is PER-SYMBOL-SINCE-TIMESTAMP (PRD section 6): a user reviews a
whole symbol as of a moment, not individual events. Acknowledging a symbol marks
every currently-pending event for it as reviewed; a genuinely new event (a later
session) surfaces again because it is created unacknowledged.

Events are one-per (user, symbol, exchange, event_date) via the unique
constraint (migration 0003), so recomputing on each dashboard load is an
idempotent upsert -- an already-surfaced session is refreshed in place, never
duplicated, and an already-acknowledged session is never resurrected.
"""
from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.change_event import ChangeEvent


async def record_change_event(
    db: AsyncSession,
    *,
    user_id: int,
    symbol: str,
    exchange: str,
    event_date: date,
    score: float,
    dominant_factor: str,
    explanation: str,
) -> None:
    """Idempotent upsert of a surfaced change.

    On conflict (same user/symbol/exchange/date):
      - if still unacknowledged -> refresh score/explanation (recompute may differ)
      - if already acknowledged -> leave it untouched (WHERE clause below is false,
        so no update and no insert -- the acknowledged row stays as it was)
    """
    stmt = pg_insert(ChangeEvent).values(
        user_id=user_id,
        symbol=symbol.upper(),
        exchange=exchange.upper(),
        event_date=event_date,
        score=score,
        dominant_factor=dominant_factor,
        explanation=explanation,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_change_event_user_symbol_date",
        set_={
            "score": stmt.excluded.score,
            "dominant_factor": stmt.excluded.dominant_factor,
            "explanation": stmt.excluded.explanation,
        },
        where=ChangeEvent.acknowledged_at.is_(None),
    )
    await db.execute(stmt)
    await db.commit()


async def acknowledge_symbol(
    db: AsyncSession,
    user_id: int,
    symbol: str,
    exchange: str,
    now: datetime | None = None,
) -> int:
    """Mark every currently-pending event for this (user, symbol, exchange) as
    reviewed as of `now`. Per-symbol-since-timestamp. Returns rows affected."""
    now = now or datetime.now(timezone.utc)
    result = await db.execute(
        update(ChangeEvent)
        .where(
            ChangeEvent.user_id == user_id,
            ChangeEvent.symbol == symbol.upper(),
            ChangeEvent.exchange == exchange.upper(),
            ChangeEvent.acknowledged_at.is_(None),
        )
        .values(acknowledged_at=now)
    )
    await db.commit()
    return result.rowcount or 0


async def get_unacknowledged_events(
    db: AsyncSession, user_id: int
) -> list[ChangeEvent]:
    """All still-pending events for a user, highest score first."""
    rows = (
        await db.execute(
            select(ChangeEvent)
            .where(
                ChangeEvent.user_id == user_id,
                ChangeEvent.acknowledged_at.is_(None),
            )
            .order_by(ChangeEvent.score.desc())
        )
    ).scalars().all()
    return list(rows)


async def unacknowledged_symbols(db: AsyncSession, user_id: int) -> set[str]:
    rows = (
        await db.execute(
            select(ChangeEvent.symbol)
            .where(
                ChangeEvent.user_id == user_id,
                ChangeEvent.acknowledged_at.is_(None),
            )
            .distinct()
        )
    ).scalars().all()
    return set(rows)


async def symbol_ack_timestamp(
    db: AsyncSession, user_id: int, symbol: str, exchange: str
) -> datetime | None:
    """The most recent point this symbol was reviewed (the 'since' timestamp)."""
    return (
        await db.execute(
            select(func.max(ChangeEvent.acknowledged_at)).where(
                ChangeEvent.user_id == user_id,
                ChangeEvent.symbol == symbol.upper(),
                ChangeEvent.exchange == exchange.upper(),
            )
        )
    ).scalar_one_or_none()