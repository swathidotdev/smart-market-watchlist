"""Manual Phase-B check. Fetches a REAL quote + benchmark via yfinance, then runs
the SAME exercise function against the demo provider — proving the swap.

Run:  python scripts/check_providers.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data_providers.base import MarketDataProvider
from app.data_providers.demo_provider import DemoProvider
from app.data_providers.factory import get_provider
from app.data_providers.yfinance_provider import YFinanceProvider


async def exercise(provider: MarketDataProvider) -> None:
    print(f"\n=== provider: {provider.name} ===")
    quote = await provider.get_quote("RELIANCE", "NSE")
    print(
        f"RELIANCE  price={quote.price:.2f}  prev={quote.previous_close:.2f}  "
        f"chg={quote.day_change_pct:+.2f}%  vol={quote.volume:,}  as_of={quote.as_of.date()}"
    )
    bars = await provider.get_daily_bars("RELIANCE", "NSE", 5)
    print(f"last {len(bars)} daily closes: {[b.close for b in bars]}")

    bench = await provider.get_benchmark(5)
    print(f"^NSEI last close: {bench[-1].close:.2f}  ({len(bench)} bars)")


async def main() -> None:
    # Identical code path, two providers — the swap proof.
    await exercise(YFinanceProvider())
    await exercise(DemoProvider())

    # And the config-driven factory (whatever DATA_PROVIDER is set to):
    print("\n=== factory (DATA_PROVIDER) ===")
    await exercise(get_provider())


if __name__ == "__main__":
    asyncio.run(main())