"""The provider boundary. Everything above this layer depends ONLY on these
types and this ABC â€” never on yfinance (or any future SDK) directly.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime


class ProviderError(Exception):
    """Any data-provider failure. Callers (the poller in Phase C) catch this at
    the provider-call boundary and degrade that one symbol's freshness â€” a
    single symbol's failure never takes down a batch (RULES.md: per-symbol
    isolation)."""


class SymbolNotFound(ProviderError):
    """Provider returned no data (delisted, typo, wrong exchange suffix)."""


@dataclass(frozen=True)
class Bar:
    """One daily OHLCV bar, identified by its trading date."""

    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class Quote:
    """A latest-known snapshot. `as_of` is the market timestamp the data
    represents (not fetch time) â€” freshness logic (Phase D) compares it to now
    and to market hours."""

    symbol: str          # canonical base symbol, e.g. "RELIANCE"
    exchange: str        # "NSE" | "BSE"
    price: float         # latest known price
    previous_close: float
    volume: int          # volume for the latest session
    as_of: datetime      # tz-aware
    currency: str = "INR"

    @property
    def day_change(self) -> float:
        return self.price - self.previous_close

    @property
    def day_change_pct(self) -> float:
        if self.previous_close == 0:
            return 0.0
        return (self.price - self.previous_close) / self.previous_close * 100.0


class MarketDataProvider(ABC):
    """The narrow interface the whole backend depends on. Three methods, no more.

    A new provider (Upstox) is added by implementing this class â€” nothing
    else in the codebase changes.
    """

    name: str = "base"

    @abstractmethod
    async def get_quote(self, symbol: str, exchange: str) -> Quote:
        """Latest-known quote for one symbol. Raises SymbolNotFound / ProviderError."""

    @abstractmethod
    async def get_daily_bars(
        self, symbol: str, exchange: str, lookback_days: int = 60
    ) -> list[Bar]:
        """Trailing daily bars, oldest-first, up to `lookback_days` sessions.
        Raises SymbolNotFound / ProviderError."""

    @abstractmethod
    async def get_benchmark(self, lookback_days: int = 60) -> list[Bar]:
        """Trailing daily bars for the market benchmark (Nifty 50), oldest-first.
        Raises ProviderError."""