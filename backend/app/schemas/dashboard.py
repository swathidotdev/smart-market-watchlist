from datetime import date, datetime

from pydantic import BaseModel

from app.schemas.common import FreshnessOut


class FeedItemOut(BaseModel):
    symbol: str
    exchange: str
    price: float | None
    day_change_pct: float | None
    direction: str          # "up" | "down" | "flat"
    score: float
    dominant_factor: str
    explanation: str
    event_date: date
    freshness: FreshnessOut


class WatchlistRowOut(BaseModel):
    symbol: str
    exchange: str
    price: float | None
    previous_close: float | None
    day_change_pct: float | None
    direction: str
    volume: int | None
    freshness: FreshnessOut
    flagged: bool


class DashboardOut(BaseModel):
    baseline_at: datetime | None
    meaningful_change_count: int
    feed: list[FeedItemOut]
    watchlist: list[WatchlistRowOut]