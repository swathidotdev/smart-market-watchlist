from fastapi import APIRouter, HTTPException

from app.api.deps import CurrentUser, DbSession
from app.core.last_check.acknowledgment import (
    acknowledge_symbol,
    get_unacknowledged_events,
)
from app.data_providers.symbols import is_valid_symbol, normalize_symbol
from app.schemas.acknowledge import AcknowledgeRequest, AcknowledgeResponse

router = APIRouter(tags=["acknowledge"])


@router.post("/acknowledge", response_model=AcknowledgeResponse)
async def acknowledge(
    payload: AcknowledgeRequest, current_user: CurrentUser, db: DbSession
) -> AcknowledgeResponse:
    symbol = normalize_symbol(payload.symbol)
    if not is_valid_symbol(symbol):
        raise HTTPException(status_code=422, detail=f"Unknown symbol: {symbol!r}")
    n = await acknowledge_symbol(db, current_user.id, symbol, payload.exchange)
    remaining = await get_unacknowledged_events(db, current_user.id)
    return AcknowledgeResponse(acknowledged=n, remaining=len(remaining))