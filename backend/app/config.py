"""Application settings and environment configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite:///./watchlist.db"
    cache_ttl_seconds: int = 300
    meaningful_change_threshold: float = 5.0


settings = Settings()
