"""Read-side view assembly: observation rows -> a display summary, and rows ->
Bars for the engine. Keeps the API routes thin (ARCHITECTURE.md). Read-only,
no provider calls -- the request path only reads what the poller persisted.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.freshness import FreshnessState, assess_freshness
from app.data_providers.base import Bar
from app.models.market_observation import MarketObservation


@dataclass(frozen=True)
class MarketSummary:
    has_data: bool
    price: float | None
    previous_close: float | None
    day_change_pct: float | None
    volume: int | None
    direction: int
    freshness: FreshnessState
    as_of_date: date | None


async def load_observations(
    db: AsyncSession, symbol: str, exchange: str, limit: int = 90
) -> list[MarketObservation]:
    rows = (
        await db.execute(
            select(MarketObservation)
            .where(
                MarketObservation.symbol == symbol.upper(),
                MarketObservation.exchange == exchange.upper(),
            )
            .order_by(MarketObservation.obs_date)
        )
    ).scalars().all()
    return list(rows)[-limit:]


def to_bars(rows: list[MarketObservation]) -> list[Bar]:
    return [
        Bar(date=r.obs_date, open=r.open, high=r.high, low=r.low,
            close=r.close, volume=r.volume)
        for r in rows
    ]


def summarize(
    rows: list[MarketObservation], now: datetime | None = None
) -> MarketSummary:
    now = now or datetime.now(timezone.utc)
    if not rows:
        return MarketSummary(
            False, None, None, None, None, 0, FreshnessState.UNAVAILABLE, None
        )
    latest = rows[-1]
    prev = rows[-2] if len(rows) >= 2 else None
    previous_close = prev.close if prev else latest.open
    price = latest.close
    day_change_pct = (
        (price - previous_close) / previous_close * 100.0 if previous_close else 0.0
    )
    direction = 1 if price > previous_close else (-1 if price < previous_close else 0)
    freshness = assess_freshness(latest.fetched_at, now=now)
    return MarketSummary(
        True, price, previous_close, day_change_pct, latest.volume,
        direction, freshness, latest.obs_date,
    )