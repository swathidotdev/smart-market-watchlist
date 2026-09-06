"""The real provider. This is the ONLY module in the backend that imports
yfinance (and, transitively, pandas). All yfinance quirks — the .NS/.BO
suffixes, the ^NSEI benchmark ticker, NaN handling, the blocking-call thread
wrap — are contained here.

This is the default Yahoo Finance provider.
"""
from __future__ import annotations

import asyncio
import logging
import math
from datetime import datetime, timezone

import yfinance as yf

from app.data_providers.base import (
    Bar,
    MarketDataProvider,
    ProviderError,
    Quote,
    SymbolNotFound,
)
from app.data_providers.symbols import Exchange, normalize_symbol

logger = logging.getLogger(__name__)

BENCHMARK_TICKER = "^NSEI"  # Nifty 50 index (yfinance convention)
_SUFFIX = {Exchange.NSE: ".NS", Exchange.BSE: ".BO"}


class YFinanceProvider(MarketDataProvider):
    name = "yfinance"

    # -- public interface ---------------------------------------------------

    async def get_quote(self, symbol: str, exchange: str) -> Quote:
        ticker = self._ticker(symbol, exchange)
        bars = await self._history(ticker, period="7d")
        if not bars:
            raise SymbolNotFound(f"No data for {ticker}")
        latest = bars[-1]
        # During a live session the last daily bar is today's forming bar, so its
        # close == latest price and bars[-2] == the true previous close.
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
        ticker = self._ticker(symbol, exchange)
        bars = await self._history(ticker, period=self._period_for(lookback_days))
        if not bars:
            raise SymbolNotFound(f"No daily bars for {ticker}")
        return bars[-lookback_days:]

    async def get_benchmark(self, lookback_days: int = 60) -> list[Bar]:
        bars = await self._history(BENCHMARK_TICKER, period=self._period_for(lookback_days))
        if not bars:
            raise ProviderError(f"No benchmark data for {BENCHMARK_TICKER}")
        return bars[-lookback_days:]

    # -- helpers (yfinance-specific, stay in this file) ---------------------

    def _ticker(self, symbol: str, exchange: str) -> str:
        try:
            ex = Exchange(exchange.strip().upper())
        except ValueError as exc:
            raise ProviderError(f"Unknown exchange: {exchange!r}") from exc
        return f"{normalize_symbol(symbol)}{_SUFFIX[ex]}"

    async def _history(self, ticker: str, *, period: str) -> list[Bar]:
        # yfinance is blocking; keep the event loop free.
        return await asyncio.to_thread(self._history_sync, ticker, period)

    def _history_sync(self, ticker: str, period: str) -> list[Bar]:
        try:
            df = yf.Ticker(ticker).history(
                period=period, interval="1d", auto_adjust=False
            )
        except Exception as exc:  # yfinance raises assorted network/parse errors
            logger.warning("yfinance history failed for %s: %s", ticker, exc)
            raise ProviderError(f"yfinance history failed for {ticker}: {exc}") from exc

        if df is None or df.empty:
            return []

        bars: list[Bar] = []
        for idx, row in df.iterrows():
            close = float(row["Close"])
            if math.isnan(close):
                continue  # skip holiday/placeholder rows
            vol = row["Volume"]
            volume = 0 if (vol is None or (isinstance(vol, float) and math.isnan(vol))) else int(vol)
            bars.append(
                Bar(
                    date=idx.date(),
                    open=float(row["Open"]),
                    high=float(row["High"]),
                    low=float(row["Low"]),
                    close=close,
                    volume=volume,
                )
            )
        return bars

    @staticmethod
    def _period_for(lookback_days: int) -> str:
        # Named yfinance periods, padded so weekends/holidays still leave enough
        # trading sessions to satisfy `lookback_days`.
        if lookback_days <= 5:
            return "7d"
        if lookback_days <= 25:
            return "1mo"
        if lookback_days <= 60:
            return "3mo"
        if lookback_days <= 120:
            return "6mo"
        if lookback_days <= 250:
            return "1y"
        return "2y"