from pydantic import BaseModel, Field


class AcknowledgeRequest(BaseModel):
    symbol: str = Field(min_length=1, max_length=32)
    exchange: str = Field(default="NSE", max_length=8)


class AcknowledgeResponse(BaseModel):
    acknowledged: int   # events marked reviewed
    remaining: int      # pending events still unacknowledged for this user