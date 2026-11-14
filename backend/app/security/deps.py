"""Request-level security: admin token for privileged actions and a small in-memory rate limiter."""
from __future__ import annotations

import hmac
import threading
import time
from collections import defaultdict, deque

from fastapi import Depends, Header, HTTPException, Request, status

from app.core.config import get_settings


def require_admin(x_admin_token: str | None = Header(default=None, alias="X-Admin-Token")) -> None:
    expected = get_settings().admin_token.get_secret_value()
    if not expected:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Privileged actions are disabled: ADMIN_TOKEN is not configured on the server.")
    if not x_admin_token or not hmac.compare_digest(x_admin_token.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "A valid admin token is required (X-Admin-Token header).")


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


def write_rate_limit(limit: int, window_seconds: float):  # noqa: ANN201
    """Limit for state-changing company endpoints, with the same limit for every caller but separate buckets.

    Sessions that may write (password sessions, admin) are counted per company (admin: per IP); everyone else, whose
    request the endpoint will refuse anyway, is counted in a separate per-IP bucket. Refused attempts therefore stay
    limited but can no longer use up the allowance of legitimate editors who share an IP (e.g. behind a proxy)."""
    from app.security.auth import Principal, get_principal

    def dependency(request: Request, principal: Principal = Depends(get_principal)) -> None:
        client = request.client.host if request.client else "unknown"
        if principal.is_admin:
            key = f"write:admin:{client}"
        elif principal.can_write and principal.company_id is not None:
            key = f"write:company:{principal.company_id}"
        else:
            key = f"write-refused:{client}"
        limiter.check(key, limit, window_seconds)

    return dependency
