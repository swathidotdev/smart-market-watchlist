"""A surfaced, scored change for a user+symbol. Written by the engine (via
acknowledgment.record_change_event) and acknowledged per-symbol.

acknowledged_at NULL == unacknowledged (still surfaces as new).

Unique on (user_id, symbol, exchange, event_date): one event per user per symbol
per session, so recomputing on each dashboard load upserts in place rather than
creating duplicates -- this is what stops an acknowledged change re-surfacing.
"""
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Float,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class ChangeEvent(Base):
    __tablename__ = "change_events"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "symbol", "exchange", "event_date",
            name="uq_change_event_user_symbol_date",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    exchange: Mapped[str] = mapped_column(String(8), nullable=False)
    event_date: Mapped[date] = mapped_column(Date, nullable=False)

    score: Mapped[float] = mapped_column(Float, nullable=False)
    dominant_factor: Mapped[str] = mapped_column(String(32), nullable=False)
    explanation: Mapped[str] = mapped_column(String(255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )