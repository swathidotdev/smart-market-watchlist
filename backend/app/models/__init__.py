# Import every model here so Base.metadata is fully populated
# (Alembic autogenerate and migrations rely on this).
from app.models.change_event import ChangeEvent
from app.models.market_observation import MarketObservation
from app.models.user import User
from app.models.user_check import UserCheck
from app.models.watchlist_item import WatchlistItem

__all__ = [
    "User",
    "WatchlistItem",
    "MarketObservation",
    "UserCheck",
    "ChangeEvent",
]