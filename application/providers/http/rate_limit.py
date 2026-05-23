# -*- coding: utf-8 -*-
"""Async token-bucket rate limiter."""
import asyncio
import time


class TokenBucket:
    """Simple per-process token bucket.

    Coroutines call `acquire()` and are made to wait until a token is
    available. Tokens refill continuously at `rate` per second up to `burst`.
    """

    def __init__(self, rate: float, burst: int) -> None:
        self._rate = max(rate, 0.001)
        self._capacity = max(burst, 1)
        self._tokens = float(self._capacity)
        self._updated = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            while True:
                now = time.monotonic()
                elapsed = now - self._updated
                self._tokens = min(self._capacity, self._tokens + elapsed * self._rate)
                self._updated = now
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    return
                wait = (1.0 - self._tokens) / self._rate
                await asyncio.sleep(wait)
