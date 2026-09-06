"""In-memory, symbol-keyed TTL cache. One process, async-lock guarded.

Keyed by (symbol, exchange), NOT by user: a symbol many users watch is fetched
once per TTL window and served to all of them (ARCHITECTURE.md). Deliberately
not Redis at this scale -- this is the ONLY sanctioned shared mutable state
(RULES.md).
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass
class _Entry(Generic[T]):
    value: T
    expires_at: float


class TTLCache(Generic[T]):
    def __init__(self, ttl_seconds: int) -> None:
        self._ttl = ttl_seconds
        self._store: dict[str, _Entry[T]] = {}
        self._lock = asyncio.Lock()

    @staticmethod
    def key(symbol: str, exchange: str) -> str:
        return f"{symbol.upper()}:{exchange.upper()}"

    async def get(self, key: str) -> T | None:
        async with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            if entry.expires_at < time.monotonic():
                self._store.pop(key, None)
                return None
            return entry.value

    async def set(self, key: str, value: T) -> None:
        async with self._lock:
            self._store[key] = _Entry(value, time.monotonic() + self._ttl)

    async def clear(self) -> None:
        async with self._lock:
            self._store.clear()