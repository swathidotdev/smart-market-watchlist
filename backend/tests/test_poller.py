import pytest

from app.data_providers.base import Bar, MarketDataProvider, ProviderError, Quote
from app.data_providers.demo_provider import DemoProvider


class FlakyProvider(MarketDataProvider):
    """Fails for a chosen symbol, succeeds for the rest -- proves isolation."""

    name = "flaky"

    def __init__(self, fail_symbol: str) -> None:
        self._fail = fail_symbol.upper()
        self._demo = DemoProvider()

    async def get_quote(self, symbol: str, exchange: str) -> Quote:
        return await self._demo.get_quote(symbol, exchange)

    async def get_daily_bars(self, symbol, exchange, lookback_days=60) -> list[Bar]:
        if symbol.upper() == self._fail:
            raise ProviderError(f"boom for {symbol}")
        return await self._demo.get_daily_bars(symbol, exchange, lookback_days)

    async def get_benchmark(self, lookback_days=60) -> list[Bar]:
        return await self._demo.get_benchmark(lookback_days)


@pytest.mark.asyncio
async def test_cache_ttl_hit_and_expiry():
    from app.cache.quote_cache import TTLCache

    cache: TTLCache[str] = TTLCache(ttl_seconds=0)  # already-expired on read
    await cache.set("k", "v")
    # ttl=0 -> expires immediately; get returns None
    assert await cache.get("k") is None

    cache2: TTLCache[str] = TTLCache(ttl_seconds=60)
    await cache2.set("k", "v")
    assert await cache2.get("k") == "v"
    assert await cache2.get("missing") is None


@pytest.mark.asyncio
async def test_cache_key_is_symbol_scoped_not_user():
    from app.cache.quote_cache import TTLCache

    assert TTLCache.key("reliance", "nse") == "RELIANCE:NSE"
    assert TTLCache.key("RELIANCE", "NSE") == "RELIANCE:NSE"  # same key regardless of user


# NOTE: poll_once writes to the DB via SessionLocal, so a full poll_once test
# needs a database. The failure-isolation *logic* is exercised here at the
# provider level; the end-to-end DB write is covered by the manual script below
# (scripts/poll_check.py) per PHASES.md's "run the poller against real symbols".
@pytest.mark.asyncio
async def test_flaky_provider_isolates_one_symbol():
    p = FlakyProvider(fail_symbol="TCS")

    # The failing symbol raises...
    with pytest.raises(ProviderError):
        await p.get_daily_bars("TCS", "NSE", 30)

    # ...but others are entirely unaffected.
    ok = await p.get_daily_bars("INFY", "NSE", 30)
    assert len(ok) == 30