"""Manual Phase-F end-to-end check. Seeds curated demo observations, then drives
every endpoint over HTTP (in-process ASGI) and asserts the contrast beat + the
acknowledge loop.

Run from backend/:  python -m scripts.api_check
(Requires DB migrated. Does NOT need the server running or DATA_PROVIDER set --
it seeds with DemoProvider directly.)
"""
import asyncio

from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, select

from app.core.security import hash_password
from app.data_providers.demo_provider import DemoProvider
from app.db.session import SessionLocal
from app.jobs.poller import poll_once
from app.main import app
from app.models.change_event import ChangeEvent
from app.models.user import User
from app.models.user_check import UserCheck
from app.models.watchlist_item import WatchlistItem

EMAIL = "apicheck@example.com"
PASSWORD = "password123"
SYMBOLS = ["RELIANCE", "TCS", "INFY", "HDFCBANK"]


async def _reset_and_seed_watchlist() -> int:
    """Ensure the user exists, wipe its prior state, and seed the 4 curated
    symbols on its watchlist BEFORE polling. Returns the user id."""
    async with SessionLocal() as db:
        user = (
            await db.execute(select(User).where(User.email == EMAIL))
        ).scalar_one_or_none()
        if user is None:
            user = User(email=EMAIL, password_hash=hash_password(PASSWORD))
            db.add(user)
            await db.flush()

        # clean slate for repeatable runs
        await db.execute(delete(ChangeEvent).where(ChangeEvent.user_id == user.id))
        await db.execute(delete(UserCheck).where(UserCheck.user_id == user.id))
        await db.execute(delete(WatchlistItem).where(WatchlistItem.user_id == user.id))
        await db.flush()

        # seed the curated symbols so the poller has them to fetch
        db.add_all(
            [WatchlistItem(user_id=user.id, symbol=s, exchange="NSE") for s in SYMBOLS]
        )
        await db.commit()
        return user.id


async def _login(c: AsyncClient) -> dict:
    """Register if new, otherwise log in. Robust to any register failure."""
    r = await c.post("/auth/register", json={"email": EMAIL, "password": PASSWORD})
    if r.status_code == 201:
        token = r.json()["access_token"]
    else:
        r = await c.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert r.status_code == 200, f"login failed: {r.status_code} {r.text}"
        token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


async def main() -> None:
    # 1. Seed watchlist FIRST, then poll -> curated symbols get observations.
    await _reset_and_seed_watchlist()
    print("seeding curated demo observations...")
    summary = await poll_once(provider=DemoProvider())
    print("seed summary:", summary)
    assert summary["symbols_ok"] == len(SYMBOLS), (
        f"expected {len(SYMBOLS)} symbols polled, got {summary['symbols_ok']} "
        f"-- watchlist seeding/order problem"
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # 2. Auth (robust)
        h = await _login(c)

        # NOTE: watchlist already seeded in the DB above. Still exercise the
        # validation failure paths through the API.
        bad = await c.post("/watchlist", json={"symbol": "NOTREAL", "exchange": "NSE"}, headers=h)
        assert bad.status_code == 422, f"invalid symbol should be 422, got {bad.status_code}"
        dup = await c.post("/watchlist", json={"symbol": "RELIANCE", "exchange": "NSE"}, headers=h)
        assert dup.status_code == 409, f"duplicate should be 409, got {dup.status_code}"

        wl = (await c.get("/watchlist", headers=h)).json()
        assert len(wl["items"]) == 4, f"expected 4 items, got {len(wl['items'])}"

        # 3. Dashboard -- the contrast beat
        d = (await c.get("/dashboard", headers=h)).json()
        flagged = {f["symbol"] for f in d["feed"]}
        quiet = {row["symbol"] for row in d["watchlist"] if not row["flagged"]}
        print(f"\nmeaningful changes: {d['meaningful_change_count']}")
        for f in d["feed"]:
            print(f"  FLAGGED {f['symbol']:9} {f['direction']:4} "
                  f"score={f['score']:.2f}  {f['explanation']}")
        print(f"  quiet: {sorted(quiet)}")

        assert flagged == {"RELIANCE"}, f"expected only RELIANCE flagged, got {flagged}"
        reliance = next(f for f in d["feed"] if f["symbol"] == "RELIANCE")
        assert reliance["direction"] == "down", "RELIANCE fell while market rose"
        assert reliance["dominant_factor"] == "market"
        assert quiet == {"TCS", "INFY", "HDFCBANK"}
        tcs = next(r for r in d["watchlist"] if r["symbol"] == "TCS")
        assert tcs["direction"] == "up" and tcs["flagged"] is False

        # 4. Stock detail -- show-your-work
        det = (await c.get("/stock/RELIANCE?exchange=NSE", headers=h)).json()
        comp = det["components"]
        print(f"\nRELIANCE detail: score={det['score']:.2f}  "
              f"vol={comp['volatility_ratio']:.2f}x  "
              f"mkt={comp['market_excess_pp']:+.2f}pp  "
              f"volume={comp['volume_ratio']:.2f}x  "
              f"({len(det['history'])} history bars)")
        assert comp is not None and len(det["history"]) > 0

        # 5. Acknowledge loop
        ack = (await c.post("/acknowledge", json={"symbol": "RELIANCE"}, headers=h)).json()
        print(f"\nacknowledged RELIANCE: {ack}")
        assert ack["acknowledged"] >= 1 and ack["remaining"] == 0

        d2 = (await c.get("/dashboard", headers=h)).json()
        print(f"after ack -> meaningful changes: {d2['meaningful_change_count']}")
        assert d2["meaningful_change_count"] == 0, "acked change must not re-surface"

    print("\nPhase F end-to-end checks passed.")


if __name__ == "__main__":
    asyncio.run(main())