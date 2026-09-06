from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "Smart Market Watchlist"
    environment: str = "development"
    data_provider: str = "yfinance"

    # asyncpg URL for the app; Alembic reads this too.
    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/smw"

    jwt_secret: str = "dev-only-change-me"
    jwt_algorithm: str = "HS256"
    jwt_expires_minutes: int = 60 * 24

    cors_origins: list[str] = ["http://localhost:5173"]

        # Poller
    poll_interval_seconds: int = 300      # how often the background poller runs
    poll_lookback_days: int = 60          # daily bars fetched/stored per symbol per poll
    enable_poller: bool = True            # off in tests / when running one-off scripts

    # Cache
    quote_cache_ttl_seconds: int = 60     # symbol-keyed TTL; one fetch serves all watchers

@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()