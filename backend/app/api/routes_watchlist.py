from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.data_providers.symbols import (
    is_valid_exchange,
    is_valid_symbol,
    normalize_symbol,
)
from app.models.watchlist_item import WatchlistItem
from app.schemas.watchlist import WatchlistItemCreate, WatchlistItemOut, WatchlistOut

router = APIRouter(prefix="/watchlist", tags=["watchlist"])


@router.get("", response_model=WatchlistOut)
async def list_watchlist(current_user: CurrentUser, db: DbSession) -> WatchlistOut:
    rows = (
        await db.execute(
            select(WatchlistItem)
            .where(WatchlistItem.user_id == current_user.id)
            .order_by(WatchlistItem.symbol)
        )
    ).scalars().all()
    return WatchlistOut(items=list(rows))


@router.post("", response_model=WatchlistItemOut, status_code=status.HTTP_201_CREATED)
async def add_symbol(
    payload: WatchlistItemCreate, current_user: CurrentUser, db: DbSession
) -> WatchlistItem:
    symbol = normalize_symbol(payload.symbol)
    exchange = payload.exchange.strip().upper()
    if not is_valid_exchange(exchange):
        raise HTTPException(status_code=422, detail=f"Unknown exchange: {payload.exchange!r}")
    if not is_valid_symbol(symbol):
        raise HTTPException(status_code=422, detail=f"Unknown symbol: {payload.symbol!r}")

    existing = await db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.symbol == symbol,
            WatchlistItem.exchange == exchange,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail=f"{symbol} is already on your watchlist")

    item = WatchlistItem(user_id=current_user.id, symbol=symbol, exchange=exchange)
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return item


@router.delete("/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_symbol(
    symbol: str, current_user: CurrentUser, db: DbSession, exchange: str = "NSE"
) -> None:
    item = await db.scalar(
        select(WatchlistItem).where(
            WatchlistItem.user_id == current_user.id,
            WatchlistItem.symbol == normalize_symbol(symbol),
            WatchlistItem.exchange == exchange.strip().upper(),
        )
    )
    if item is None:
        raise HTTPException(status_code=404, detail=f"{symbol} is not on your watchlist")
    await db.delete(item)
    await db.commit()