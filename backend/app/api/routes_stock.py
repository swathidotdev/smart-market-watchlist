from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.core.change_engine import evaluate_change
from app.core.change_engine.scoring import STATUS_OK
from app.core.freshness import FreshnessState
from app.core.market_view import load_observations, summarize, to_bars
from app.data_providers.symbols import is_valid_symbol, normalize_symbol
from app.jobs.poller import BENCHMARK_EXCHANGE, BENCHMARK_SYMBOL
from app.schemas.common import FreshnessOut
from app.schemas.stock import ComponentBreakdownOut, HistoryBarOut, StockDetailOut

router = APIRouter(prefix="/stock", tags=["stock"])


def _direction(d: int) -> str:
    return "up" if d > 0 else ("down" if d < 0 else "flat")


@router.get("/{symbol}", response_model=StockDetailOut)
async def get_stock(
    symbol: str, current_user: CurrentUser, db: DbSession, exchange: str = "NSE"
) -> StockDetailOut:
    symbol = normalize_symbol(symbol)
    if not is_valid_symbol(symbol):
        raise HTTPException(status_code=422, detail=f"Unknown symbol: {symbol!r}")

    obs = await load_observations(db, symbol, exchange)
    if not obs:
        raise HTTPException(status_code=404, detail=f"No data yet for {symbol}")

    now = datetime.now(timezone.utc)
    summary = summarize(obs, now)
    bench_bars = to_bars(await load_observations(db, BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE))
    ev = evaluate_change(to_bars(obs), bench_bars, baseline_date=None)  # latest session
    r = ev.result

    components = None
    if r.status == STATUS_OK and r.components is not None:
        c = r.components
        components = ComponentBreakdownOut(
            return_pct=c.return_pct,
            volatility_ratio=c.volatility_ratio,
            market_excess_pp=c.market_excess_pp,
            volume_ratio=c.volume_ratio,
            volatility_norm=c.volatility,
            market_norm=c.market,
            volume_norm=c.volume,
        )

    history = [
        HistoryBarOut(date=o.obs_date, close=o.close, volume=o.volume) for o in obs[-20:]
    ]

    return StockDetailOut(
        symbol=symbol,
        exchange=exchange.strip().upper(),
        price=summary.price,
        previous_close=summary.previous_close,
        day_change_pct=summary.day_change_pct,
        volume=summary.volume,
        direction=_direction(summary.direction),
        freshness=FreshnessOut(state=summary.freshness.value, label=summary.freshness.label),
        status=r.status,
        score=r.score,
        dominant_factor=r.dominant_factor,
        explanation=ev.explanation,
        components=components,
        history=history,
    )