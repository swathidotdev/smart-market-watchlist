"""The swap seam. Selecting a provider is reading one config value — this is what
makes 'switch to Upstox' a configuration change, not a rewrite.
"""
from __future__ import annotations

from app.config import settings
from app.data_providers.base import MarketDataProvider
from app.data_providers.demo_provider import DemoProvider
from app.data_providers.yfinance_provider import YFinanceProvider

_REGISTRY: dict[str, type[MarketDataProvider]] = {
    "yfinance": YFinanceProvider,
    "demo": DemoProvider,
    # "upstox": UpstoxProvider,   # future — add the class, add this line, done.
}


def get_provider() -> MarketDataProvider:
    key = settings.data_provider.strip().lower()
    try:
        return _REGISTRY[key]()
    except KeyError as exc:
        raise ValueError(
            f"Unknown DATA_PROVIDER {settings.data_provider!r}; "
            f"valid: {sorted(_REGISTRY)}"
        ) from exc