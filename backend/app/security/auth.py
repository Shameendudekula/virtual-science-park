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


def issue_token(company_id: int, ttl_minutes: int | None = None) -> tuple[str, int]:
    exp = int(time.time()) + 60 * (ttl_minutes or get_settings().token_ttl_minutes)
    payload = _b64(json.dumps({"cid": company_id, "exp": exp}, separators=(",", ":")).encode())
    sig = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    return f"{payload}.{sig}", exp


def decode_token(token: str) -> int | None:
    try:
        payload, sig = token.split(".")
    except ValueError:
        return None
    expected = _b64(hmac.new(_secret(), payload.encode(), hashlib.sha256).digest())
    if not hmac.compare_digest(sig, expected):
        return None
    try:
        data = json.loads(_unb64(payload))
    except (ValueError, json.JSONDecodeError):
        return None
    if not isinstance(data.get("cid"), int) or data.get("exp", 0) < time.time():
        return None
    return data["cid"]


@dataclass
class Principal:
    company_id: int | None
    is_admin: bool

    def can_access(self, company_id: int) -> bool:
        return self.is_admin or self.company_id == company_id


def get_principal(
    authorization: str | None = Header(default=None), x_admin_token: str | None = Header(default=None, alias="X-Admin-Token"),
) -> Principal:
    admin = get_settings().admin_token.get_secret_value()
    is_admin = bool(admin and x_admin_token and hmac.compare_digest(x_admin_token.encode(), admin.encode()))
    company_id = None
    if authorization and authorization.lower().startswith("bearer "):
        company_id = decode_token(authorization[7:].strip())
        if company_id is None and not is_admin:
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired or invalid. Please sign in again.")
    return Principal(company_id, is_admin)


def require_company(company_id: int, principal: Principal) -> None:
    if principal.can_access(company_id):
        return
    if principal.company_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to this company's workspace to view or change its private data.")
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your session belongs to a different company workspace.")


PrincipalDep = Depends(get_principal)
