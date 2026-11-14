"""Public demo is read-only: every state-changing endpoint is protected server-side, by direct API calls.

Roles: anonymous (no token) · demo session (password-free, read-only) · password session (its own company may change data)
· admin (X-Admin-Token: collectors, demo reset, and any company's data)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time

import pytest
from sqlalchemy import select

from app.security.auth import READ_ONLY_MESSAGE
from tests.conftest import company_id
from tests.sessions import demo_headers, password_headers

ADMIN = {"X-Admin-Token": "test-admin-token"}


def _writes(db):
    """Every company-data write endpoint, as (method, path, json) for Ocean Harvesting."""
    from app.models import CompanyClaim, Recommendation

    oh = company_id(db, "ocean-harvesting")
    rec = db.scalar(select(Recommendation).where(Recommendation.company_id == oh, Recommendation.is_current.is_(True)))
    claim = db.scalar(select(CompanyClaim).where(CompanyClaim.company_id == oh, CompanyClaim.claim_type == "inferred"))
    return [
        ("PATCH", f"/api/companies/{oh}/profile", {"add_claims": [{"field": "research_interest", "value": "Permission test claim"}]}),
        ("PATCH", f"/api/companies/{oh}/profile", {"priorities": {"find_funding": 3}}),
        ("POST", f"/api/companies/{oh}/claims/{claim.id}/review", {"action": "reject"}),
        ("PUT", f"/api/companies/{oh}/priorities", {"weights": {"testing_facilities": 3}}),
        ("POST", f"/api/recommendations/{rec.id}/save", {}),
        ("POST", f"/api/recommendations/{rec.id}/dismiss", {}),
        ("POST", f"/api/recommendations/{rec.id}/explore", None),
        ("POST", f"/api/recommendations/{rec.id}/restore", None),
    ]


def _state(db):
    """Snapshot of the shared demo state that the write endpoints could change."""
    from app.models import CompanyClaim, CompanyPriority, ProfileRevision, Recommendation, SavedRecommendation, SearchHistory

    db.expire_all()
    oh = company_id(db, "ocean-harvesting")
    return {
        "claims": sorted((c.id, c.status) for c in db.scalars(select(CompanyClaim).where(CompanyClaim.company_id == oh))),
        "priorities": sorted((p.key, p.weight) for p in db.scalars(select(CompanyPriority).where(CompanyPriority.company_id == oh))),
        "recs": sorted((r.id, r.status) for r in db.scalars(select(Recommendation).where(Recommendation.company_id == oh))),
        "saved": db.query(SavedRecommendation).count(),
        "revisions": db.query(ProfileRevision).count(),
        "history": db.query(SearchHistory).count(),
    }


def _call(client, method, path, body, headers):
    return client.request(method, path, json=body, headers=headers or {})


def test_anonymous_and_demo_sessions_cannot_change_anything(client, db):
    before = _state(db)
    demo = demo_headers(client, db)
    other_company = password_headers(client, db, "roxtec")
    from app.security.deps import limiter

    for method, path, body in _writes(db):
        limiter.reset()  # rejected attempts count towards the write limit too; keep each endpoint's checks independent
        anon = _call(client, method, path, body, None)
        assert anon.status_code == 401 and anon.json()["error"]["code"] == "unauthorized", (method, path)
        ro = _call(client, method, path, body, demo)
        assert ro.status_code == 403, (method, path, ro.text)
        assert ro.json()["error"] == {"code": "forbidden", "message": READ_ONLY_MESSAGE}
        other = _call(client, method, path, body, other_company)
        assert other.status_code == 403 and "different company" in other.json()["error"]["message"], (method, path)
        assert _call(client, method, path, body, {"Authorization": "Bearer forged.token"}).status_code == 401
    for path in ("/api/demo/reset", "/api/collectors/vinnova/run?mode=snapshot"):
        assert client.post(path).status_code == 401
        assert client.post(path, headers=demo).status_code == 401  # a company session is never an admin
        assert client.post(path, headers=other_company).status_code == 401
    assert _state(db) == before, "a rejected request changed shared demo state"


def test_demo_session_keeps_full_read_access(client, db):
    oh = company_id(db, "ocean-harvesting")
    h = demo_headers(client, db)
    for ep in ("overview", "profile", "claims", "opportunities", "technologies", "collaborations", "graph", "recommendations",
               "focus", "funding", "innovation-brief", "innovation-brief?format=pdf"):
        assert client.get(f"/api/companies/{oh}/{ep}", headers=h).status_code == 200, ep
    rec = client.get(f"/api/companies/{oh}/recommendations", headers=h).json()
    rec_id = (rec["items"] if isinstance(rec, dict) else rec)[0]["id"]
    assert client.get(f"/api/recommendations/{rec_id}", headers=h).status_code == 200
    r = client.get("/api/search", params={"q": "wave energy funding", "company_id": oh}, headers=h)
    assert r.status_code == 200 and r.json()["results"]
    me = client.get("/api/auth/me", headers=h).json()
    assert me["authenticated"] and me["read_only"] is True and me["is_admin"] is False


def test_password_session_can_change_its_own_company(client, db, reset_after):
    from app.models import CompanyClaim, CompanyPriority, Recommendation

    oh = company_id(db, "ocean-harvesting")
    h = password_headers(client, db)
    assert client.get("/api/auth/me", headers=h).json()["read_only"] is False
    r = client.patch(f"/api/companies/{oh}/profile", headers=h, json={"add_claims": [{"field": "research_interest", "value": "Permission test claim"}]})
    assert r.status_code == 200
    added = db.scalar(select(CompanyClaim).where(CompanyClaim.company_id == oh, CompanyClaim.value == "Permission test claim"))
    assert added is not None and added.claim_type == "user_provided"
    assert client.post(f"/api/companies/{oh}/claims/{added.id}/review", headers=h, json={"action": "reject"}).status_code == 200
    assert client.put(f"/api/companies/{oh}/priorities", headers=h, json={"weights": {"testing_facilities": 3}}).status_code == 200
    db.expire_all()
    assert db.scalar(select(CompanyPriority.weight).where(CompanyPriority.company_id == oh, CompanyPriority.key == "testing_facilities")) == 3
    rec_id = db.scalar(select(Recommendation.id).where(Recommendation.company_id == oh, Recommendation.is_current.is_(True)))
    assert client.post(f"/api/recommendations/{rec_id}/save", headers=h, json={}).json()["status"] == "saved"
    assert client.post(f"/api/recommendations/{rec_id}/restore", headers=h).json()["status"] == "open"


def test_admin_keeps_privileged_workflows(client, db, reset_after):
    oh = company_id(db, "ocean-harvesting")
    r = client.patch(f"/api/companies/{oh}/profile", headers=ADMIN, json={"add_claims": [{"field": "research_interest", "value": "Admin test claim"}]})
    assert r.status_code == 200
    assert client.post("/api/demo/reset", headers={"X-Admin-Token": "wrong"}).status_code == 401
    assert client.post("/api/demo/reset", headers=ADMIN).status_code == 200


def test_session_scope_cannot_be_forged_and_legacy_tokens_are_read_only(client, db):
    from app.security.auth import _b64, _secret

    oh = company_id(db, "ocean-harvesting")
    demo_token = demo_headers(client, db)["Authorization"][7:]
    payload, sig = demo_token.split(".")
    data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
    assert data["scp"] == "read"
    data["scp"] = "write"
    upgraded = _b64(json.dumps(data, separators=(",", ":")).encode()) + "." + sig  # signature no longer matches
    body = {"weights": {"testing_facilities": 3}}
    assert client.put(f"/api/companies/{oh}/priorities", headers={"Authorization": f"Bearer {upgraded}"}, json=body).status_code == 401
    # A validly signed token from before scopes existed (no "scp") is treated as read-only.
    legacy_payload = _b64(json.dumps({"cid": oh, "exp": int(time.time()) + 600}, separators=(",", ":")).encode())
    legacy = legacy_payload + "." + _b64(hmac.new(_secret(), legacy_payload.encode(), hashlib.sha256).digest())
    lh = {"Authorization": f"Bearer {legacy}"}
    assert client.get(f"/api/companies/{oh}/overview", headers=lh).status_code == 200
    assert client.put(f"/api/companies/{oh}/priorities", headers=lh, json=body).status_code == 403


def test_search_history_stays_private(client, db):
    from app.models import SearchHistory

    oh = company_id(db, "ocean-harvesting")
    demo = demo_headers(client, db)
    before = db.query(SearchHistory).count()
    client.get("/api/search", params={"q": "Which funding fits our wave energy work?", "company_id": oh}, headers=demo)
    db.expire_all()
    assert db.query(SearchHistory).count() == before, "a public demo visitor's question must not be stored"
    denied = client.get("/api/search/history", headers=demo)
    assert denied.status_code == 403 and denied.json()["error"]["code"] == "forbidden"
    assert client.get("/api/search/history").status_code == 401
    owner = password_headers(client, db)
    client.get("/api/search", params={"q": "Which testing facilities suit our prototype?", "company_id": oh}, headers=owner)
    mine = client.get("/api/search/history", headers=owner).json()
    assert mine and mine[0]["query"] == "Which testing facilities suit our prototype?"
    assert all(x["query"] != "Which testing facilities suit our prototype?" for x in client.get("/api/search/history", headers=password_headers(client, db, "cleura")).json())


def test_login_and_demo_login_have_separate_rate_limits(client, db):
    codes = [client.post("/api/auth/login", json={"username": "nobody", "password": "wrong-password"}).status_code for _ in range(11)]
    assert codes[:10] == [401] * 10 and codes[10] == 429  # 10 password attempts per minute
    assert client.post("/api/auth/demo-login", json={"company_id": company_id(db, "cleura")}).status_code == 200


def test_opening_many_demo_workspaces_does_not_block_password_sign_in(client, db):
    for _ in range(15):
        assert client.post("/api/auth/demo-login", json={"company_id": company_id(db, "cleura")}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "nobody", "password": "wrong-password"}).status_code == 401


def test_write_rate_limit(client, db):
    from app.models import Recommendation

    oh = company_id(db, "ocean-harvesting")
    h = password_headers(client, db)
    rec_id = db.scalar(select(Recommendation.id).where(Recommendation.company_id == oh, Recommendation.is_current.is_(True)))
    codes = [client.post(f"/api/recommendations/{rec_id}/restore", headers=h).status_code for _ in range(31)]
    assert codes[:30] == [200] * 30 and codes[30] == 429


@pytest.mark.parametrize("scope", ["admin", "", "WRITE"])
def test_only_known_scopes_can_be_issued(scope):
    from app.security.auth import issue_token

    with pytest.raises(ValueError):
        issue_token(1, scope=scope)


# ------------------------------------------------------------------------------------------------ Fix #2.1 (through the real app)
def test_malformed_authorization_header_gives_401_not_500(client, db):
    oh = company_id(db, "ocean-harvesting")
    token = password_headers(client, db)["Authorization"][7:]
    payload = token.split(".")[0]
    for bad in (f"Bearer {payload}.éabc".encode("latin-1"), b"Bearer \xff\xfe", f"Bearer {token}x".encode()):
        r = client.get(f"/api/companies/{oh}/overview", headers={"Authorization": bad})
        assert r.status_code == 401, bad
        assert r.json()["error"] == {"code": "unauthorized", "message": "Session expired or invalid. Please sign in again."}


def test_refused_writes_do_not_block_a_password_session_on_the_same_ip(client, db, reset_after):
    oh = company_id(db, "ocean-harvesting")
    demo = demo_headers(client, db)
    body = {"weights": {"testing_facilities": 2}}
    refused = [client.put(f"/api/companies/{oh}/priorities", json=body, headers=h).status_code for h in ([demo] * 20 + [{}] * 15)]
    assert set(refused[:30]) <= {401, 403} and refused[30:] == [429] * 5  # refused attempts are still rate limited
    ok = client.put(f"/api/companies/{oh}/priorities", json=body, headers=password_headers(client, db))
    assert ok.status_code == 200, "an editor sharing the IP keeps its own allowance"
