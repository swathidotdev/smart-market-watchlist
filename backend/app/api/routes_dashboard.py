from datetime import datetime, timezone

from fastapi import APIRouter
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.core.change_engine import evaluate_change
from app.core.change_engine.scoring import STATUS_OK
from app.core.freshness import FreshnessState
from app.core.last_check.acknowledgment import (
    get_unacknowledged_events,
    record_change_event,
)
from app.core.last_check.baseline import open_dashboard
from app.core.market_view import load_observations, summarize, to_bars
from app.jobs.poller import BENCHMARK_EXCHANGE, BENCHMARK_SYMBOL
from app.models.watchlist_item import WatchlistItem
from app.schemas.common import FreshnessOut
from app.schemas.dashboard import DashboardOut, FeedItemOut, WatchlistRowOut

router = APIRouter(tags=["dashboard"])


def _direction(d: int) -> str:
    return "up" if d > 0 else ("down" if d < 0 else "flat")


def _fresh(state: FreshnessState) -> FreshnessOut:
    return FreshnessOut(state=state.value, label=state.label)


@router.get("/dashboard", response_model=DashboardOut)
async def get_dashboard(current_user: CurrentUser, db: DbSession) -> DashboardOut:
    now = datetime.now(timezone.utc)
    baseline_at = await open_dashboard(db, current_user.id, now=now)
    baseline_date = baseline_at.date() if baseline_at else None

    items = (
        await db.execute(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == current_user.id)
            .order_by(WatchlistItem.symbol)
        )
    ).scalars().all()

    bench_bars = to_bars(await load_observations(db, BENCHMARK_SYMBOL, BENCHMARK_EXCHANGE))

    summaries = {}
    for item in items:
        obs_rows = await load_observations(db, item.symbol, item.exchange)
        summary = summarize(obs_rows, now)
        summaries[(item.symbol.upper(), item.exchange.upper())] = summary
        if summary.has_data:
            ev = evaluate_change(to_bars(obs_rows), bench_bars, baseline_date)
            if ev.crosses_threshold and ev.result.status == STATUS_OK and ev.result.obs_date:
                await record_change_event(
                    db,
                    user_id=current_user.id,
                    symbol=item.symbol,
                    exchange=item.exchange,
                    event_date=ev.result.obs_date,
                    score=ev.result.score,
                    dominant_factor=ev.result.dominant_factor,
                    explanation=ev.explanation,
                )

    pending = await get_unacknowledged_events(db, current_user.id)  # score desc
    pending_syms = {(e.symbol.upper(), e.exchange.upper()) for e in pending}

    feed: list[FeedItemOut] = []
    for e in pending:
        s = summaries.get((e.symbol.upper(), e.exchange.upper()))
        feed.append(
            FeedItemOut(
                symbol=e.symbol,
                exchange=e.exchange,
                price=s.price if s else None,
                day_change_pct=s.day_change_pct if s else None,
                direction=_direction(s.direction if s else 0),
                score=e.score,
                dominant_factor=e.dominant_factor,
                explanation=e.explanation,
                event_date=e.event_date,
                freshness=_fresh(s.freshness if s else FreshnessState.UNAVAILABLE),
            )
        )

    watchlist: list[WatchlistRowOut] = []
    for item in items:
        s = summaries[(item.symbol.upper(), item.exchange.upper())]
        watchlist.append(
            WatchlistRowOut(
                symbol=item.symbol,
                exchange=item.exchange,
                price=s.price,
                previous_close=s.previous_close,
                day_change_pct=s.day_change_pct,
                direction=_direction(s.direction),
                volume=s.volume,
                freshness=_fresh(s.freshness),
                flagged=(item.symbol.upper(), item.exchange.upper()) in pending_syms,
            )
        )

    return DashboardOut(
        baseline_at=baseline_at,
        meaningful_change_count=len(feed),
        feed=feed,
        watchlist=watchlist,
    )