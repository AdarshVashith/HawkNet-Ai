"""Sliding-window in-process rate limiter for FastAPI.

Usage:
    @router.post("/my-endpoint")
    def my_view(
        _: Annotated[None, Depends(check_rate_limit)],
        ...
    ):

Keyed by client IP (X-Forwarded-For → Remote-addr fallback).
Returns HTTP 429 with Retry-After header when limit is exceeded.

For multi-worker / multi-process deployments, swap _windows for a Redis-backed
counter (e.g. ``redis.incr`` + ``redis.expire``).
"""

from __future__ import annotations

import time
from collections import deque
from threading import Lock
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.core.config import Settings, get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Per-IP deque of timestamps (seconds, float) within the current window.
_windows: dict[str, deque[float]] = {}
_lock = Lock()
WINDOW_SECONDS = 60.0


def _client_ip(request: Request) -> str:
    """Extract the real client IP from X-Forwarded-For or direct connection."""
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Take the first (leftmost / originating) IP
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_rate_limit(
    request: Request,
    settings: Annotated[Settings, Depends(get_settings)],
) -> None:
    """FastAPI dependency — raises HTTP 429 if the client exceeds the rate limit.

    No-op when ``rate_limit_enabled=false``.
    """
    if not settings.rate_limit_enabled:
        return

    ip = _client_ip(request)
    limit = settings.rate_limit_per_minute
    now = time.monotonic()
    cutoff = now - WINDOW_SECONDS

    with _lock:
        window = _windows.setdefault(ip, deque())
        # Evict timestamps outside the current window
        while window and window[0] < cutoff:
            window.popleft()

        if len(window) >= limit:
            retry_after = int(WINDOW_SECONDS - (now - window[0])) + 1
            logger.warning(
                "Rate limit exceeded for %s (%d/%d per minute)", ip, len(window), limit
            )
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: {limit} requests per 60 seconds.",
                headers={"Retry-After": str(retry_after)},
            )

        window.append(now)
