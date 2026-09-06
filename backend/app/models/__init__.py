# Import every model here so Base.metadata is fully populated
# (Alembic autogenerate and create-time reflection both rely on this).
from app.models.user import User
from app.models.watchlist_item import WatchlistItem

__all__ = ["User", "WatchlistItem"]