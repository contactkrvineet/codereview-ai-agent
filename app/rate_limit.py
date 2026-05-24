"""
Simple in-memory rate limiter.

For a production deployment with multiple workers, swap this for Redis-backed
limiting. For a single-instance demo on Render free tier, in-memory is sufficient.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import Deque, Dict

from .config import RATE_LIMIT_PER_DAY, RATE_LIMIT_PER_HOUR


class RateLimiter:
    """Sliding-window rate limiter keyed on arbitrary identifier (typically client IP)."""

    def __init__(self):
        self._hour_buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._day_buckets: Dict[str, Deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> tuple[bool, str]:
        """
        Returns (allowed, message). If not allowed, message explains why.
        Records the request if allowed.
        """
        now = time.time()
        hour_ago = now - 3600
        day_ago = now - 86400

        with self._lock:
            hour_bucket = self._hour_buckets[key]
            day_bucket = self._day_buckets[key]

            # Evict old entries
            while hour_bucket and hour_bucket[0] < hour_ago:
                hour_bucket.popleft()
            while day_bucket and day_bucket[0] < day_ago:
                day_bucket.popleft()

            if len(hour_bucket) >= RATE_LIMIT_PER_HOUR:
                oldest = hour_bucket[0]
                wait_min = int((oldest + 3600 - now) / 60) + 1
                return False, (
                    f"Rate limit reached ({RATE_LIMIT_PER_HOUR} reviews per hour). "
                    f"Try again in ~{wait_min} minute(s)."
                )

            if len(day_bucket) >= RATE_LIMIT_PER_DAY:
                return False, (
                    f"Daily limit reached ({RATE_LIMIT_PER_DAY} reviews per day). "
                    "Try again tomorrow, or deploy your own instance from the source code."
                )

            hour_bucket.append(now)
            day_bucket.append(now)
            return True, ""


# Module-level singleton — fine for a single-worker deployment
rate_limiter = RateLimiter()
