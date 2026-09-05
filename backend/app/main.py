"""FastAPI application entrypoint."""

from fastapi import FastAPI

app = FastAPI(title="Smart Market Watchlist")


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}
