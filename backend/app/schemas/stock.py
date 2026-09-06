from datetime import date

from pydantic import BaseModel

from app.schemas.common import FreshnessOut


class ComponentBreakdownOut(BaseModel):
    return_pct: float
    volatility_ratio: float     # "Nx normal swing"
    market_excess_pp: float     # signed pp vs Nifty
    volume_ratio: float         # "Nx normal volume"
    volatility_norm: float      # normalized values that feed the score
    market_norm: float
    volume_norm: float


class HistoryBarOut(BaseModel):
    date: date
    close: float
    volume: int


class StockDetailOut(BaseModel):
    symbol: str
    exchange: str
    price: float | None
    previous_close: float | None
    day_change_pct: float | None
    volume: int | None
    direction: str
    freshness: FreshnessOut
    status: str
    score: float
    dominant_factor: str
    explanation: str
    components: ComponentBreakdownOut | None
    history: list[HistoryBarOut]