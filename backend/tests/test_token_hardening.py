"""Fix #2.1: malformed tokens are rejected with 401 (never a 500), and refused writes cannot use up editors' rate limit.

Database-independent: these tests call the security functions directly, so they also run with VSP_TEST_NO_DB=1."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from app.security import auth
from app.security.deps import limiter, write_rate_limit


def _signed(data: dict) -> str:
    payload = auth._b64(json.dumps(data, separators=(",", ":")).encode())
    return payload + "." + auth._b64(hmac.new(auth._secret(), payload.encode(), hashlib.sha256).digest())


def _principal(authorization: str | None):
    return auth.get_principal(authorization=authorization, x_admin_token=None)


def _valid() -> str:
    return auth.issue_token(6, scope=auth.SCOPE_WRITE)[0]


MALFORMED = {
    "non-ascii signature": lambda t: t.split(".")[0] + ".é" + t.split(".")[1][1:],
    "non-ascii payload": lambda t: "é" + t,
    "emoji": lambda t: t + "\U0001F600",
    "zero-width character": lambda t: t[:10] + "​" + t[10:],
    "nul byte": lambda t: t + "\x00",
    "oversized": lambda t: t + "A" * 5000,
    "empty": lambda t: "",
    "single dot": lambda t: ".",
    "no dot": lambda t: t.replace(".", ""),
    "three parts": lambda t: t + ".x",
    "empty signature": lambda t: t.split(".")[0] + ".",
    "empty payload": lambda t: "." + t.split(".")[1],
    "signature with spaces": lambda t: t.split(".")[0] + ". " + t.split(".")[1],
    "base64 padding junk": lambda t: t.split(".")[0] + "==." + t.split(".")[1],
    "truncated signature": lambda t: t[:-3],
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_tokens_are_rejected_with_401(name):
    token = MALFORMED[name](_valid())
    assert auth.decode_session(token) is None
    with pytest.raises(HTTPException) as exc:
        _principal(f"Bearer {token}")
    assert exc.value.status_code == 401
    assert exc.value.detail == "Session expired or invalid. Please sign in again."  # no token details echoed


def test_valid_tokens_still_verify():
    assert auth.decode_session(_valid()) == (6, auth.SCOPE_WRITE)
    assert auth.decode_session(auth.issue_token(6)[0]) == (6, auth.SCOPE_READ)
    p = _principal(f"Bearer {_valid()}")
    assert (p.company_id, p.can_write, p.is_admin) == (6, True, False)


@pytest.mark.parametrize("exp", ["9999999999", None, True, [1], {"t": 1}])
def test_signed_tokens_with_malformed_expiry_are_rejected(exp):
    data = {"cid": 6, "scp": "write"} if exp is None else {"cid": 6, "scp": "write", "exp": exp}
    assert auth.decode_session(_signed(data)) is None


@pytest.mark.parametrize("payload", ["[1, 2]", '"text"', "123", "null"])
def test_signed_non_object_payloads_are_rejected(payload):
    p = auth._b64(payload.encode())
    token = p + "." + auth._b64(hmac.new(auth._secret(), p.encode(), hashlib.sha256).digest())
    assert auth.decode_session(token) is None


def test_signature_check_is_unchanged():
    payload, sig = _valid().split(".")
    other = base64.urlsafe_b64encode(b"x" * 32).rstrip(b"=").decode()
    assert auth.decode_session(f"{payload}.{other}") is None
    assert auth.decode_session(_signed({"cid": 6, "exp": int(time.time()) - 5, "scp": "write"})) is None  # expiry enforced


# ------------------------------------------------------------------------------------------------ write rate limit
def _request(ip: str = "203.0.113.5") -> Request:
    return Request({"type": "http", "method": "POST", "path": "/", "headers": [], "client": (ip, 40000)})


def _hits(dep, principal, n, ip="203.0.113.5"):
    codes = []
    for _ in range(n):
        try:
            dep(_request(ip), principal)
            codes.append(200)
        except HTTPException as e:
            codes.append(e.status_code)
    return codes


def test_refused_writes_cannot_use_up_an_editors_allowance():
    limiter.reset()
    dep = write_rate_limit(30, 60)
    anonymous = auth.Principal(None, False, False)
    demo = auth.Principal(6, False, False)
    editor = auth.Principal(6, False, True)
    # 40 refused attempts from one shared IP (anonymous and demo sessions share the "refused" bucket) ...
    assert _hits(dep, anonymous, 20)[-1] == 200
    codes = _hits(dep, demo, 20)
    assert codes[:10] == [200] * 10 and codes[10:] == [429] * 10  # ... are still limited, at the same 30/min
    # ... but the company's password session from the same IP keeps its full allowance.
    assert _hits(dep, editor, 30) == [200] * 30
    assert _hits(dep, editor, 1) == [429]  # and is itself still limited
    limiter.reset()


def test_write_buckets_are_separate_per_company_and_for_admin():
    limiter.reset()
    dep = write_rate_limit(2, 60)
    a, b, admin = auth.Principal(6, False, True), auth.Principal(7, False, True), auth.Principal(None, True, False)
    assert _hits(dep, a, 3) == [200, 200, 429]
    assert _hits(dep, b, 2) == [200, 200]
    assert _hits(dep, admin, 2) == [200, 200]
    limiter.reset()
