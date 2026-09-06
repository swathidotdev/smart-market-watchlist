import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


def test_openapi_registers_all_routes():
    paths = app.openapi()["paths"]
    for p in ("/watchlist", "/dashboard", "/stock/{symbol}", "/acknowledge",
              "/auth/register", "/auth/login"):
        assert p in paths, f"missing route {p}"


@pytest.mark.asyncio
async def test_protected_routes_require_auth():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # No token -> rejected before any DB access.
        assert (await c.get("/dashboard")).status_code in (401, 403)
        assert (await c.get("/watchlist")).status_code in (401, 403)
        assert (await c.post("/acknowledge", json={"symbol": "RELIANCE"})).status_code in (401, 403)