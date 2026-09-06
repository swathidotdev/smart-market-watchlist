"""Manual Phase-D check: run the engine against REAL observations the Phase-C
poller wrote to the DB. Confirms the score/explanation reads sensibly on live
data, per PHASES.md.

Run from backend/:  python -m scripts.engine_check
(Requires observations in the DB -- run `python -m scripts.poll_check` first.)
"""
import asyncio

from sqlalchemy import select

from app.core.change_engine import evaluate_change
from app.core.freshness import assess_freshness
from app.data_providers.base import Bar
from app.db.session import SessionLocal
from app.jobs.poller import BENCHMARK_EXCHANGE, BENCHMARK_SYMBOL
from app.models.market_observation import MarketObservation

SYMBOL, EXCHANGE = "RELIANCE", "NSE"


def _to_bars(rows) -> list[Bar]:
    return [
        Bar(date=r.obs_date, open=r.open, high=r.high, low=r.low, close=r.close, volume=r.volume)
        for r in rows
    ]


async def _load(symbol: str, exchange: str):
    async with SessionLocal() as db:
        rows = (
            await db.execute(
                select(MarketObservation)
                .where(MarketObservation.symbol == symbol,
                       MarketObservation.exchange == exchange)
                .order_by(MarketObservation.obs_date)
            )
        ).scalars().all()
    return rows


async def main() -> None:
    stock_rows = await _load(SYMBOL, EXCHANGE)
    bench_rows = await _load(BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE)

    if len(stock_rows) < 12:
        print(f"Only {len(stock_rows)} observations for {SYMBOL}. "
              f"Run `python -m scripts.poll_check` a few times first.")
        return

    stock, bench = _to_bars(stock_rows), _to_bars(bench_rows)

    print(f"=== {SYMBOL}.{EXCHANGE}: {len(stock)} sessions, {len(bench)} benchmark sessions ===")

    # First-time view (no baseline) -> assess latest session.
    ev = evaluate_change(stock, bench, baseline_date=None)
    r = ev.result
    print(f"latest session : {r.obs_date}")
    print(f"status         : {r.status}")
    print(f"score          : {r.score:.3f}   crosses={ev.crosses_threshold}")
    print(f"dominant       : {r.dominant_factor}")
    print(f"explanation    : {ev.explanation}")
    if r.components:
        c = r.components
        print(f"  return       : {c.return_pct:+.2f}%")
        print(f"  volatility   : {c.volatility_ratio:.2f}x normal swing")
        print(f"  market       : {c.market_excess_pp:+.2f}pp vs Nifty (norm {c.market:.2f})")
        print(f"  volume       : {c.volume_ratio:.2f}x normal")

    fresh = assess_freshness(stock_rows[-1].fetched_at)
    print(f"freshness      : {fresh.label}")


if __name__ == "__main__":
    asyncio.run(main())