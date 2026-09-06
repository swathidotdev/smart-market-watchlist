"""market history: market_observations, user_checks, change_events

Revision ID: 0002
Revises: 0001
"""
import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "market_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=8), nullable=False),
        sa.Column("obs_date", sa.Date(), nullable=False),
        sa.Column("open", sa.Float(), nullable=False),
        sa.Column("high", sa.Float(), nullable=False),
        sa.Column("low", sa.Float(), nullable=False),
        sa.Column("close", sa.Float(), nullable=False),
        sa.Column("volume", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("source", sa.String(length=16), server_default="yfinance", nullable=False),
        sa.Column(
            "fetched_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint(
            "symbol", "exchange", "obs_date", name="uq_observation_symbol_date"
        ),
    )
    op.create_index(
        "ix_market_observations_symbol", "market_observations", ["symbol"]
    )

    op.create_table(
        "user_checks",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column(
            "checked_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_user_checks_user_id", "user_checks", ["user_id"])
    op.create_index("ix_user_checks_checked_at", "user_checks", ["checked_at"])

    op.create_table(
        "change_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("exchange", sa.String(length=8), nullable=False),
        sa.Column("event_date", sa.Date(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("dominant_factor", sa.String(length=32), nullable=False),
        sa.Column("explanation", sa.String(length=255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_change_events_user_id", "change_events", ["user_id"])
    op.create_index("ix_change_events_symbol", "change_events", ["symbol"])


def downgrade() -> None:
    op.drop_index("ix_change_events_symbol", table_name="change_events")
    op.drop_index("ix_change_events_user_id", table_name="change_events")
    op.drop_table("change_events")

    op.drop_index("ix_user_checks_checked_at", table_name="user_checks")
    op.drop_index("ix_user_checks_user_id", table_name="user_checks")
    op.drop_table("user_checks")

    op.drop_index("ix_market_observations_symbol", table_name="market_observations")
    op.drop_table("market_observations")