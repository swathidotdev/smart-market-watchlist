"""Provider-neutral symbol whitelist and exchange enum.

This is the input-validation gate: nothing arbitrary reaches a provider. It is
deliberately provider-NEUTRAL — the .NS/.BO suffix mapping is a yfinance
convention and lives in yfinance_provider.py, so this file (and the whitelist)
survives a swap to Upstox unchanged.
"""
from __future__ import annotations

from enum import Enum


class Exchange(str, Enum):
    NSE = "NSE"
    BSE = "BSE"


# Well-known, liquid NSE large-cap tickers (broadly the Nifty 50 set). This is a
# validation whitelist — the requirement is "real, resolvable tickers we allow",
# not "exact current index membership", which drifts at each index review and is
# not something the product depends on. Extend/refresh freely later.
NIFTY_50: frozenset[str] = frozenset(
    {
        "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK", "HINDUNILVR",
        "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK", "LT", "AXISBANK",
        "BAJFINANCE", "ASIANPAINT", "MARUTI", "HCLTECH", "SUNPHARMA",
        "TITAN", "ULTRACEMCO", "WIPRO", "NESTLEIND", "POWERGRID", "NTPC",
        "TATAMOTORS", "TATASTEEL", "JSWSTEEL", "ADANIENT", "ADANIPORTS",
        "COALINDIA", "ONGC", "GRASIM", "BAJAJFINSV", "TECHM", "HDFCLIFE",
        "SBILIFE", "BRITANNIA", "DIVISLAB", "DRREDDY", "CIPLA", "EICHERMOT",
        "HEROMOTOCO", "BAJAJ-AUTO", "HINDALCO", "INDUSINDBK", "APOLLOHOSP",
        "TATACONSUM", "BPCL", "LTIM", "SHRIRAMFIN", "TRENT",
    }
)

VALID_SYMBOLS: frozenset[str] = NIFTY_50


def normalize_symbol(symbol: str) -> str:
    """Canonical form used everywhere above the provider layer."""
    return symbol.strip().upper()


def is_valid_symbol(symbol: str) -> bool:
    return normalize_symbol(symbol) in VALID_SYMBOLS


def is_valid_exchange(exchange: str) -> bool:
    return exchange.strip().upper() in {e.value for e in Exchange}