"""The one component that runs independent of a request.

Each cycle:
  1. Poll ^NSEI once, upsert its bars (benchmark history for market-relative scoring).
  2. Build the deduplicated union of watched (symbol, exchange) across ALL users.
  3. For each, fetch recent daily bars THROUGH THE PROVIDER ABSTRACTION and upsert.

Per-symbol failure isolation is mandatory (RULES.md): one symbol's failure is
caught, logged, and skipped -- it never stops the rest of the batch. No LLM
calls, no direct yfinance import here -- only the provider interface.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.cache.quote_cache import TTLCache
from app.config import settings
from app.data_providers.base import Bar, MarketDataProvider, ProviderError
from app.data_providers.factory import get_provider
from app.db.session import SessionLocal
from app.models.market_observation import MarketObservation
from app.models.watchlist_item import WatchlistItem

logger = logging.getLogger(__name__)

# Reserved pseudo-symbol under which the benchmark's bars are stored.
BENCHMARK_SYMBOL = "^NSEI"
BENCHMARK_EXCHANGE = "IDX"

# Module-level cache instance (the sanctioned shared state).
quote_cache: TTLCache[list[Bar]] = TTLCache(settings.quote_cache_ttl_seconds)


async def _watched_symbols() -> list[tuple[str, str]]:
    """Deduplicated union of (symbol, exchange) across every user's watchlist."""
    async with SessionLocal() as db:
        rows = await db.execute(select(WatchlistItem.symbol, WatchlistItem.exchange))
        pairs = {(s.upper(), e.upper()) for s, e in rows.all()}
    return sorted(pairs)


async def _upsert_bars(
    symbol: str, exchange: str, bars: list[Bar], source: str
) -> int:
    """Idempotent write: (symbol, exchange, obs_date) conflicts update in place."""
    if not bars:
        return 0
    async with SessionLocal() as db:
        stmt = pg_insert(MarketObservation).values(
            [
                {
                    "symbol": symbol,
                    "exchange": exchange,
                    "obs_date": b.date,
                    "open": b.open,
                    "high": b.high,
                    "low": b.low,
                    "close": b.close,
                    "volume": b.volume,
                    "source": source,
                }
                for b in bars
            ]
        )
        stmt = stmt.on_conflict_do_update(
            constraint="uq_observation_symbol_date",
            set_={
                "open": stmt.excluded.open,
                "high": stmt.excluded.high,
                "low": stmt.excluded.low,
                "close": stmt.excluded.close,
                "volume": stmt.excluded.volume,
                "source": stmt.excluded.source,
                "fetched_at": __import__("sqlalchemy").func.now(),
            },
        )
        await db.execute(stmt)
        await db.commit()
    return len(bars)


async def _fetch_bars_cached(
    provider: MarketDataProvider, symbol: str, exchange: str
) -> list[Bar]:
    key = TTLCache.key(symbol, exchange)
    cached = await quote_cache.get(key)
    if cached is not None:
        return cached
    bars = await provider.get_daily_bars(symbol, exchange, settings.poll_lookback_days)
    await quote_cache.set(key, bars)
    return bars


async def poll_once(provider: MarketDataProvider | None = None) -> dict:
    """Run exactly one poll cycle. Returns a small summary for logging/verification.

    Provider is injectable so tests/scripts can pass the demo or a failing one.
    """
    provider = provider or get_provider()
    summary = {"benchmark": 0, "symbols_ok": 0, "symbols_failed": 0, "rows_written": 0}

    # 1. Benchmark, isolated on its own try/except.
    try:
        bench = await provider.get_benchmark(settings.poll_lookback_days)
        written = await _upsert_bars(BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE, bench, provider.name)
        summary["benchmark"] = written
        summary["rows_written"] += written
    except ProviderError as exc:
        logger.warning("Benchmark poll failed: %s", exc)
    except Exception:  # never let benchmark failure kill the cycle
        logger.exception("Unexpected benchmark poll error")

    # 2/3. Per-symbol, each fully isolated.
    for symbol, exchange in await _watched_symbols():
        try:
            bars = await _fetch_bars_cached(provider, symbol, exchange)
            written = await _upsert_bars(symbol, exchange, bars, provider.name)
            summary["symbols_ok"] += 1
            summary["rows_written"] += written
        except ProviderError as exc:
            summary["symbols_failed"] += 1
            logger.warning("Poll failed for %s:%s -- %s", symbol, exchange, exc)
        except Exception:
            summary["symbols_failed"] += 1
            logger.exception("Unexpected poll error for %s:%s", symbol, exchange)

    logger.info("Poll cycle complete: %s", summary)
    return summary