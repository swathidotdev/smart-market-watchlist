"""Deterministic fixture provider. Satisfies the SAME interface as the real one,
so it runs on the identical code path — it is a peer, not a facade (ARCHITECTURE.md).

Phase B scope: a deterministic-but-generic stub (stable pseudo-random walk seeded
per symbol). The CURATED contrast scenario (one anomalous mover, one
market-tracker, one quiet stock, one whipsaw) lands in Phase F.
"""
from __future__ import annotations

import random
import zlib
from datetime import date, datetime, timedelta, timezone

from app.data_providers.base import Bar, MarketDataProvider, Quote
from app.data_providers.symbols import normalize_symbol

BENCHMARK_KEY = "^NSEI"


def _last_business_days(n: int) -> list[date]:
    days: list[date] = []
    d = date.today()
    while len(days) < n:
        if d.weekday() < 5:  # Mon–Fri
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))


class DemoProvider(MarketDataProvider):
    name = "demo"

    async def get_quote(self, symbol: str, exchange: str) -> Quote:
        bars = self._series(normalize_symbol(symbol), 7)
        latest = bars[-1]
        previous_close = bars[-2].close if len(bars) >= 2 else latest.open
        as_of = datetime.combine(latest.date, datetime.min.time(), tzinfo=timezone.utc)
        return Quote(
            symbol=normalize_symbol(symbol),
            exchange=exchange.strip().upper(),
            price=latest.close,
            previous_close=previous_close,
            volume=latest.volume,
            as_of=as_of,
        )

    async def get_daily_bars(
        self, symbol: str, exchange: str, lookback_days: int = 60
    ) -> list[Bar]:
        return self._series(normalize_symbol(symbol), lookback_days)

    async def get_benchmark(self, lookback_days: int = 60) -> list[Bar]:
        # Lower daily vol than a single stock — an index moves less than its names.
        return self._series(BENCHMARK_KEY, lookback_days, base=22_000.0, daily_vol=0.006)

    # -- deterministic generator -------------------------------------------

    def _series(
        self,
        key: str,
        n: int,
        *,
        base: float | None = None,
        daily_vol: float = 0.015,
    ) -> list[Bar]:
        # zlib.crc32 gives a STABLE seed across processes; the built-in hash() of
        # a str does not (PYTHONHASHSEED randomization) and would break determinism.
        seed = zlib.crc32(key.encode())
        rng = random.Random(seed)

        price = base if base is not None else 500.0 + (seed % 3000)
        avg_volume = 1_000_000 + (seed % 5_000_000)

        bars: list[Bar] = []
        for d in _last_business_days(n):
            ret = rng.gauss(0.0, daily_vol)
            open_ = price
            close = max(1.0, price * (1.0 + ret))
            high = max(open_, close) * (1.0 + abs(rng.gauss(0.0, daily_vol / 2)))
            low = min(open_, close) * (1.0 - abs(rng.gauss(0.0, daily_vol / 2)))
            volume = int(avg_volume * (1.0 + abs(rng.gauss(0.0, 0.3))))
            bars.append(
                Bar(
                    date=d,
                    open=round(open_, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(close, 2),
                    volume=volume,
                )
            )
            price = close
        return bars