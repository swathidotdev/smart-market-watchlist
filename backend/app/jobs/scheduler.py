"""APScheduler wiring. Started/stopped by the FastAPI lifespan (main.py).

One interval job -> poll_once. No broker, no queue -- an in-process scheduler is
sufficient at this scale (RULES.md / TECH_STACK.md).
"""
from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.config import settings
from app.jobs.poller import poll_once

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


async def _run_poll() -> None:
    try:
        await poll_once()
    except Exception:
        # A whole-cycle crash must never kill the scheduler thread.
        logger.exception("poll_once raised at the top level")


def start_scheduler() -> None:
    global _scheduler
    if not settings.enable_poller:
        logger.info("Poller disabled (ENABLE_POLLER=false) -- not scheduling.")
        return
    if _scheduler is not None:
        return
    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _run_poll,
        trigger="interval",
        seconds=settings.poll_interval_seconds,
        id="market_poller",
        next_run_time=None,  # first run is triggered manually below for a warm start
        max_instances=1,
        coalesce=True,
    )
    _scheduler.start()
    logger.info(
        "Poller scheduled every %ss (warm start kicked off).",
        settings.poll_interval_seconds,
    )


def shutdown_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("Poller stopped.")