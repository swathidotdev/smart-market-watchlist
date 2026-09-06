from pydantic import BaseModel


class ErrorResponse(BaseModel):
    detail: str


class FreshnessOut(BaseModel):
    state: str   # LIVE / RECENT / DELAYED / STALE / UNAVAILABLE
    label: str   # sentence case, e.g. "Delayed"