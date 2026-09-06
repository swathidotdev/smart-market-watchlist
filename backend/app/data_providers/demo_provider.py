"""Deterministic fixture provider. Same interface as the real one, so it runs on
the identical code path -- a peer, not a facade (ARCHITECTURE.md).

CURATED CONTRAST SCENARIO (the demo's core beat). On the final session the market
(^NSEI) rises +2.5%. Against that:

  RELIANCE  -1.5%, 2.5x volume  -> FLAGGED. Fell while the market rose.
            volatility 1.5, market 4.0 (excess -4.0pp), volume 1.5
            score = 0.40*1.5 + 0.35*4.0 + 0.25*1.5 = 2.375  (>= 1.8)  [RED, but LOUD]
  TCS       +2.6%, normal volume -> not flagged. Rode the market up.
            volatility 2.6, market 0.1, volume 0
            score = 0.40*2.6 + 0.35*0.1 = 1.075  (< 1.8)             [GREEN, but QUIET]
  INFY      +2.3%, normal volume -> not flagged (score ~0.99)         [quiet]
  HDFCBANK  +2.4% final, but its history holds a mid-period WHIPSAW
            (-3% then +3%): flat end-to-end, caught by peak detection
            only when a baseline predates it -> the "not a non-event" case.

So on a first load the feed is exactly {RELIANCE} -- one meaningful change, and the
contrast (RELIANCE down/flagged vs TCS up/quiet) proves the ranking is
significance, not size. Non-curated symbols fall back to a seeded random walk.
"""
from __future__ import annotations

import random
import zlib
from datetime import date, datetime, timedelta, timezone

from app.data_providers.base import Bar, MarketDataProvider, Quote
from app.data_providers.symbols import normalize_symbol

BENCHMARK_KEY = "^NSEI"
_TOTAL_SESSIONS = 45

# symbol -> (base_close, tail). tail is the last-N (return, volume_multiple) pairs;
# everything before the tail is the calm alternating +/-1% window.
_CURATED: dict[str, tuple[float, list[tuple[float, float]]]] = {
    "RELIANCE": (1400.0, [(-0.015, 2.5)]),
    "TCS": (4000.0, [(0.026, 1.0)]),
    "INFY": (1800.0, [(0.023, 1.0)]),
    "HDFCBANK": (1700.0, [(-0.030, 2.2), (0.030, 1.0), (0.024, 1.0)]),
}


def _last_business_days(n: int) -> list[date]:
    days: list[date] = []
    d = date.today()
    while len(days) < n:
        if d.weekday() < 5:
            days.append(d)
        d -= timedelta(days=1)
    return list(reversed(days))


class DemoProvider(MarketDataProvider):
    name = "demo"

    async def get_quote(self, symbol: str, exchange: str) -> Quote:
        bars = self._bars_for(normalize_symbol(symbol))
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
        return self._bars_for(normalize_symbol(symbol), lookback_days)

    async def get_benchmark(self, lookback_days: int = 60) -> list[Bar]:
        # Calm-flat window, +2.5% on the final session.
        bars = self._curated_series(24_000.0, [(0.025, 1.0)], calm=0.0)
        return bars[-lookback_days:] if lookback_days < len(bars) else bars

    # -- dispatch: curated vs generic -------------------------------------

    def _bars_for(self, symbol: str, lookback_days: int = _TOTAL_SESSIONS) -> list[Bar]:
        if symbol in _CURATED:
            base, tail = _CURATED[symbol]
            bars = self._curated_series(base, tail)
        else:
            bars = self._generic_series(symbol, _TOTAL_SESSIONS)
        return bars[-lookback_days:] if lookback_days < len(bars) else bars

    # -- curated builder (deterministic, hand-computable) -----------------

    def _curated_series(
        self,
        base: float,
        tail: list[tuple[float, float]],
        *,
        calm: float | None = None,
        base_vol: int = 1_000_000,
    ) -> list[Bar]:
        dates = _last_business_days(_TOTAL_SESSIONS)
        n = len(dates)
        n_tail = len(tail)
        tail_start = n - n_tail  # index where the tail begins

        # returns for indices 1..n-1
        returns: list[float] = []
        for i in range(1, n):
            if i >= tail_start:
                returns.append(tail[i - tail_start][0])
            elif calm is not None:
                returns.append(calm)  # flat window (benchmark)
            else:
                returns.append(0.01 if i % 2 == 0 else -0.01)  # +/-1% alternating

        closes = [base]
        for r in returns:
            closes.append(round(closes[-1] * (1 + r), 2))

        volumes: list[int] = []
        for i in range(n):
            if i >= tail_start:
                volumes.append(int(base_vol * tail[i - tail_start][1]))
            else:
                volumes.append(base_vol)

        bars: list[Bar] = []
        for i, (d, c, v) in enumerate(zip(dates, closes, volumes)):
            open_ = closes[i - 1] if i > 0 else c
            bars.append(
                Bar(
                    date=d,
                    open=round(open_, 2),
                    high=round(max(open_, c), 2),
                    low=round(min(open_, c), 2),
                    close=c,
                    volume=v,
                )
            )
        return bars

    # -- generic fallback (Phase B walk) ----------------------------------

    def _generic_series(self, key: str, n: int) -> list[Bar]:
        seed = zlib.crc32(key.encode())
        rng = random.Random(seed)
        price = 500.0 + (seed % 3000)
        avg_volume = 1_000_000 + (seed % 5_000_000)
        bars: list[Bar] = []
        for d in _last_business_days(n):
            ret = rng.gauss(0.0, 0.015)
            open_ = price
            close = max(1.0, price * (1.0 + ret))
            high = max(open_, close) * (1.0 + abs(rng.gauss(0.0, 0.0075)))
            low = min(open_, close) * (1.0 - abs(rng.gauss(0.0, 0.0075)))
            volume = int(avg_volume * (1.0 + abs(rng.gauss(0.0, 0.3))))
            bars.append(
                Bar(date=d, open=round(open_, 2), high=round(high, 2),
                    low=round(low, 2), close=round(close, 2), volume=volume)
            )
            price = close
        return bars