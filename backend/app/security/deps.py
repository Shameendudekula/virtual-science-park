"""Request-level security: admin token for privileged actions and a small in-memory rate limiter."""
from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request, status

from app.core.config import get_settings


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    expected = get_settings().admin_token.get_secret_value()
    if not expected:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Privileged actions are disabled: ADMIN_TOKEN is not configured on the server.")
    if not x_admin_token or not hmac.compare_digest(x_admin_token.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid admin token is required (X-Admin-Token header).")


def require_admin_unless_demo(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    if get_settings().demo_mode:
        return
    require_admin(x_admin_token)


class RateLimiter:
    """Sliding-window limiter keyed by client IP + bucket. Suitable for a single-process deployment."""

    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def check(self, key: str, limit: int, window_seconds: float) -> None:
        now = time.monotonic()
        with self._lock:
            q = self._hits[key]
            while q and now - q[0] > window_seconds:
                q.popleft()
            if len(q) >= limit:
                retry = int(window_seconds - (now - q[0])) + 1
                raise HTTPException(status.HTTP_429_TOO_MANY_REQUESTS, f"Rate limit exceeded; retry in {retry}s.",
                                    headers={"Retry-After": str(retry)})
            q.append(now)

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


limiter = RateLimiter()


def rate_limit(bucket: str, limit: int, window_seconds: float):  # noqa: ANN201
    def dependency(request: Request) -> None:
        client = request.client.host if request.client else "unknown"
        limiter.check(f"{bucket}:{client}", limit, window_seconds)

    return dependency
