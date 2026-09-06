"""change_event dedup: unique (user, symbol, exchange, event_date)

Revision ID: 0003
Revises: 0002
"""
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_change_event_user_symbol_date",
        "change_events",
        ["user_id", "symbol", "exchange", "event_date"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_change_event_user_symbol_date", "change_events", type_="unique"
    )