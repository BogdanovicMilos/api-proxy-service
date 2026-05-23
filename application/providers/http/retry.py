# -*- coding: utf-8 -*-
"""Retry policy: which upstream responses are transient + backoff calculation."""
import random

TRANSIENT_STATUS: frozenset[int] = frozenset({408, 425, 429, 500, 502, 503, 504})


def compute_backoff(attempt: int, *, base: float, cap: float, jitter: float) -> float:
    """Exponential backoff with uniform jitter.

    attempt is 1-indexed; result is in seconds.
    """
    delay = min(cap, base * (2 ** (attempt - 1)))
    return delay + random.uniform(0, jitter)
