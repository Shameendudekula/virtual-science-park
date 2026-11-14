"""Company workspace authentication: one login per company, PBKDF2 password hashing, signed expiring tokens."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import logging
import secrets
import time
from dataclasses import dataclass
from functools import lru_cache

from fastapi import Depends, Header, HTTPException, status

from app.core.config import get_settings

log = logging.getLogger("vsp.auth")
PBKDF2_ITERATIONS = 390_000


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iterations)
    return f"pbkdf2_sha256${iterations}${base64.b64encode(salt).decode()}${base64.b64encode(digest).decode()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        algo, iterations, salt_b64, digest_b64 = stored.split("$")
    except ValueError:
        return False
    if algo != "pbkdf2_sha256":
        return False
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(salt_b64), int(iterations))
    return hmac.compare_digest(digest, base64.b64decode(digest_b64))


@lru_cache
def _secret() -> bytes:
    key = get_settings().secret_key.get_secret_value()
    if not key:
        log.warning("SECRET_KEY not set: using an ephemeral key; sessions end when the server restarts")
        key = secrets.token_hex(32)
    return key.encode()


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode()


def _unb64(data: str) -> bytes:
    return base64.urlsafe_b64decode(data + "=" * (-len(data) % 4))


# Session scopes. A password sign-in may change its own company's data ("write"); a password-free demo session may only
# read ("read"). The scope is inside the signed payload, so it cannot be altered without invalidating the signature.
SCOPE_WRITE = "write"
SCOPE_READ = "read"
MAX_TOKEN_LENGTH = 2048  # issued tokens are about 100 characters
READ_ONLY_MESSAGE = ("This is a read-only demo session. Sign in with the company's username and password to change "
                     "profiles, priorities or saved items.")


def issue_token(company_id: int, ttl_minutes: int | None = None, *, scope: str = SCOPE_READ) -> tuple[str, int]:
    if scope not in (SCOPE_READ, SCOPE_WRITE):
        raise ValueError("unknown session scope")
    exp = int(time.time()) + 60 * (ttl_minutes or get_settings().token_ttl_minutes)
    payload = _b64(json.dumps({"cid": company_id, "exp": exp, "scp": scope}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}", exp


def decode_session(token: str) -> tuple[int, str] | None:
    """(company id, scope) for a valid, unexpired token. Tokens without a scope (issued before scopes existed) are read-only.

    Any malformed input returns None (-> 401), never an exception: issued tokens are short ASCII strings, so anything
    non-ASCII or oversized is rejected before the signature check, which then compares ASCII bytes in constant time."""
    if not isinstance(token, str) or len(token) > MAX_TOKEN_LENGTH or not token.isascii():
        return None
    try:
        payload, sig = token.split(".")
    except ValueError:
        return None
    expected = _b64(hmac.new(_secret(), payload.encode("ascii"), hashlib.sha256).digest())
    if not hmac.compare_digest(sig.encode("ascii"), expected.encode("ascii")):
        return None
    try:
        data = json.loads(_unb64(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("cid"), int):
        return None
    exp = data.get("exp")
    if isinstance(exp, bool) or not isinstance(exp, (int, float)) or exp < time.time():
        return None
    return data["cid"], SCOPE_WRITE if data.get("scp") == SCOPE_WRITE else SCOPE_READ


def decode_token(token: str) -> int | None:
    session = decode_session(token)
    return session[0] if session else None


@dataclass
class Principal:
    company_id: int | None
    is_admin: bool
    can_write: bool = False  # True only for a password-authenticated company session

    def can_access(self, company_id: int) -> bool:
        return self.is_admin or self.company_id == company_id

    @property
    def read_only(self) -> bool:
        return self.company_id is not None and not self.can_write


def get_principal(
    authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> Principal:
    admin = get_settings().admin_token.get_secret_value()
    is_admin = bool(admin and x_admin_token and hmac.compare_digest(x_admin_token.encode(), admin.encode()))
    company_id, can_write = None, False
    if authorization and authorization.lower().startswith("bearer "):
        session = decode_session(authorization[7:].strip())
        if session is None and not is_admin:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid. Please sign in again.")
        if session is not None:
            company_id, can_write = session[0], session[1] == SCOPE_WRITE
    return Principal(company_id, is_admin, can_write)


def require_company(company_id: int, principal: Principal) -> None:
    """Read access to a company's private workspace data (any session of that company, or admin)."""
    if principal.can_access(company_id):
        return
    if principal.company_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to this company's workspace to view or change its private data.")
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your session belongs to a different company workspace.")


def require_company_write(company_id: int, principal: Principal) -> None:
    """Changes to a company's data: a password-authenticated session of that company, or admin.

    401 without a session, 403 for another company's session, 403 for a read-only (demo) session."""
    if principal.is_admin:
        return
    require_company(company_id, principal)
    if not principal.can_write:
        raise HTTPException(status.HTTP_403_FORBIDDEN, READ_ONLY_MESSAGE)


PrincipalDep = Depends(get_principal)
