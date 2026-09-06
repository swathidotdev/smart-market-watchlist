from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistItemCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", max_length=8)


class WatchlistItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    exchange: str
    created_at: datetime


class WatchlistOut(BaseModel):
    items: list[WatchlistItemOut]