"""Manual Phase-C check. Requires the DB migrated (alembic upgrade head) and,
for real data, internet. Seeds a couple of watchlist rows if none exist, runs
one poll cycle, prints how many observations landed, then proves failure
isolation with a provider that fails one symbol.

Run from backend/:  python -m scripts.poll_check
"""
import asyncio

from sqlalchemy import func, select

from app.data_providers.base import Bar, MarketDataProvider, ProviderError, Quote
from app.data_providers.demo_provider import DemoProvider
from app.db.session import SessionLocal
from app.jobs.poller import poll_once
from app.models.market_observation import MarketObservation
from app.models.user import User
from app.models.watchlist_item import WatchlistItem


class FailOneProvider(MarketDataProvider):
    name = "fail-one"

    def __init__(self, fail_symbol: str) -> None:
        self._fail = fail_symbol.upper()
        self._demo = DemoProvider()

    async def get_quote(self, symbol, exchange) -> Quote:
        return await self._demo.get_quote(symbol, exchange)

    async def get_daily_bars(self, symbol, exchange, lookback_days=60) -> list[Bar]:
        if symbol.upper() == self._fail:
            raise ProviderError(f"simulated failure for {symbol}")
        return await self._demo.get_daily_bars(symbol, exchange, lookback_days)

    async def get_benchmark(self, lookback_days=60) -> list[Bar]:
        return await self._demo.get_benchmark(lookback_days)


async def _seed_if_empty() -> None:
    async with SessionLocal() as db:
        user = (await db.execute(select(User).limit(1))).scalar_one_or_none()
        if user is None:
            from app.core.security import hash_password

            user = User(email="poller@test.local", password_hash=hash_password("password123"))
            db.add(user)
            await db.flush()
        existing = (
            await db.execute(select(func.count()).select_from(WatchlistItem))
        ).scalar_one()
        if existing == 0:
            db.add_all(
                [
                    WatchlistItem(user_id=user.id, symbol="RELIANCE", exchange="NSE"),
                    WatchlistItem(user_id=user.id, symbol="TCS", exchange="NSE"),
                    WatchlistItem(user_id=user.id, symbol="INFY", exchange="NSE"),
                ]
            )
        await db.commit()


async def _count_observations() -> int:
    async with SessionLocal() as db:
        return (
            await db.execute(select(func.count()).select_from(MarketObservation))
        ).scalar_one()


async def main() -> None:
    await _seed_if_empty()

    print("=== poll cycle #1 (demo provider, deterministic) ===")
    s1 = await poll_once(provider=DemoProvider())
    print(s1, "| total observations in DB:", await _count_observations())

    print("\n=== poll cycle #2 (same day, should UPSERT not duplicate) ===")
    s2 = await poll_once(provider=DemoProvider())
    print(s2, "| total observations in DB:", await _count_observations(),
          "(should not grow much vs #1 -- same sessions upserted)")

    print("\n=== poll cycle #3 (provider fails TCS -- isolation check) ===")
    s3 = await poll_once(provider=FailOneProvider(fail_symbol="TCS"))
    print(s3, "-> symbols_failed should be >= 1, symbols_ok should still be > 0")


if __name__ == "__main__":
    asyncio.run(main())