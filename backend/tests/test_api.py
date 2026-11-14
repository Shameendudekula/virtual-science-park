"""API behaviour: health, errors, validation, admin protection, rate limits, brief, search, focus, funding, members."""
from __future__ import annotations

from tests.conftest import company_id
from tests.sessions import password_headers


def _h(client, db, slug="ocean-harvesting"):
    return {"Authorization": "Bearer " + client.post("/api/auth/demo-login", json={"company_id": company_id(db, slug)}).json()["token"]}


def test_health(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok" and body["counts"]["companies_profiled"] == 7


def test_errors_have_consistent_shape(client):
    r = client.get("/api/companies/999999")
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"
    r = client.get("/api/companies?page=0")
    assert r.status_code == 422 and r.json()["error"]["code"] == "validation_error"


def test_security_headers(client):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff" and r.headers["X-Frame-Options"] == "DENY"


def test_collector_requires_admin_token(client):
    assert client.post("/api/collectors/vinnova/run").status_code == 401
    assert client.post("/api/collectors/vinnova/run", headers={"X-Admin-Token": "wrong"}).status_code == 401
    r = client.post("/api/collectors/ymner/run", headers={"X-Admin-Token": "test-admin-token"})
    assert r.status_code == 409 and "Ymner" in r.json()["error"]["message"]


def test_sources_never_expose_credentials(client):
    text = client.get("/api/sources").text
    assert "test-admin-token" not in text
    keys = {s["key"]: s for s in client.get("/api/sources").json()}
    assert keys["ymner"]["enabled"] is False and "401" in keys["ymner"]["license_note"]


def test_pagination(client):
    a = client.get("/api/companies", params={"page_size": 5, "page": 1}).json()
    b = client.get("/api/companies", params={"page_size": 5, "page": 2}).json()
    assert a["total"] == 56 and len(a["items"]) == 5
    assert {x["id"] for x in a["items"]}.isdisjoint({x["id"] for x in b["items"]})


def test_member_directory_lists_all_verified_members(client):
    body = client.get("/api/members").json()
    assert body["total"] >= 40 and body["verified_members"] == body["total"]
    directory_only = [m for m in body["items"] if m["profile_level"] == "directory"]
    assert directory_only and all(m["membership_url"].startswith("https://www.bluesciencepark.se/medlem/") for m in directory_only)
    assert len({m["name"] for m in body["items"]}) == body["total"]  # no duplicates


def test_directory_only_member_gets_clear_error(client, db):
    from app.models import Company

    directory = db.query(Company).filter_by(profile_level="directory").first()
    h = {"X-Admin-Token": "test-admin-token"}
    r = client.get(f"/api/companies/{directory.id}/overview", headers=h)
    assert r.status_code == 422 and "no VSP profile" in r.json()["error"]["message"]


def test_innovation_brief_json_and_pdf(client, db):
    oh, h = company_id(db, "ocean-harvesting"), _h(client, db)
    brief = client.get(f"/api/companies/{oh}/innovation-brief", headers=h).json()
    assert brief["evidence"] and brief["limitations"] and brief["executive_summary"]["bullets"]
    pdf = client.get(f"/api/companies/{oh}/innovation-brief", params={"format": "pdf"}, headers=h)
    assert pdf.status_code == 200 and pdf.content[:4] == b"%PDF"


def test_focus_view_is_compact_and_actionable(client, db):
    oh, h = company_id(db, "ocean-harvesting"), _h(client, db)
    f = client.get(f"/api/companies/{oh}/focus", headers=h).json()
    assert 1 <= len(f["top_three"]) <= 3
    for r in f["top_three"]:
        assert r["why"] and r["next_step"]
    assert len(f["deadlines"]) <= 5 and len(f["local_events"]) <= 5
    assert any(p["name"] == "Roxtec" for p in f["regional_partners"])
    assert "screened" in f["time_saved"]["message"]


def test_unified_funding_lists_sources_and_dedupes(client, db):
    from app.services.intelligence.views import dedupe_funding, dedupe_key

    oh, h = company_id(db, "ocean-harvesting"), _h(client, db)
    body = client.get(f"/api/companies/{oh}/funding", headers=h).json()
    assert {s["key"] for s in body["sources"]} == {"vinnova", "ymner", "eu_funding_tenders"}
    ymner = next(s for s in body["sources"] if s["key"] == "ymner")
    assert ymner["integrated"] is False and ymner["link"] == "https://www.ymner.com/"
    a = {"dedupe_key": dedupe_key("Wave Energy Call 2026", None), "source_name": "A", "url": "https://a"}
    b = {"dedupe_key": dedupe_key("wave energy call", None), "source_name": "B", "url": "https://b"}
    merged = dedupe_funding([a, b])
    assert len(merged) == 1 and merged[0]["also_listed_by"][0]["url"] == "https://b"


def test_natural_language_search(client, db):
    h = _h(client, db)
    r = client.get("/api/search", params={"q": "Which funding opportunities are relevant to Ocean Harvesting?"}, headers=h).json()
    assert r["query"]["intent"] == "opportunities" and r["query"]["company_name"] == "Ocean Harvesting"
    assert r["results"] and all(x["type"] == "opportunity" for x in r["results"])
    r2 = client.get("/api/search", params={"q": "Which companies have complementary expertise in marine technology?"}).json()
    assert r2["query"]["intent"] == "partners" and any(x["title"] == "Roxtec" for x in r2["results"])
    r3 = client.get("/api/search", params={"q": "What technologies could improve industrial energy systems?"}).json()
    assert r3["query"]["intent"] == "technologies" and r3["results"]
    assert "no text was generated" in r3["note"]


def test_recommendation_actions_are_company_scoped(client, db):
    from app.models import Recommendation

    oh = company_id(db, "ocean-harvesting")
    rec = db.query(Recommendation).filter_by(company_id=oh, is_current=True).first()
    assert client.post(f"/api/recommendations/{rec.id}/save").status_code == 401
    assert client.post(f"/api/recommendations/{rec.id}/save", headers=_h(client, db, "cleura")).status_code == 403
    h = password_headers(client, db)  # changing saved items needs a password session
    assert client.post(f"/api/recommendations/{rec.id}/save", headers=h).json()["status"] == "saved"
    assert client.post(f"/api/recommendations/{rec.id}/dismiss", headers=h).json()["status"] == "dismissed"
    assert client.post(f"/api/recommendations/{rec.id}/restore", headers=h).json()["status"] == "open"


def test_rate_limit_on_login(client):
    codes = [client.post("/api/auth/login", json={"username": "x", "password": "y"}).status_code for _ in range(12)]
    assert 429 in codes


def test_demo_reset_restores_clean_state(client, db):
    oh, h = company_id(db, "ocean-harvesting"), password_headers(client, db)
    r = client.patch(f"/api/companies/{oh}/profile", headers=h, json={"add_claims": [{"field": "research_interest", "value": "Underwater robotics"}]})
    assert r.status_code == 200
    assert client.post("/api/demo/reset").status_code == 401  # reset needs the admin token, also in demo mode
    assert client.post("/api/demo/reset", headers={"X-Admin-Token": "test-admin-token"}).status_code == 200
    claims = client.get(f"/api/companies/{oh}/claims", headers=_h(client, db)).json()
    assert not [c for c in claims if c["claim_type"] == "user_provided"]


def test_focus_top_three_respects_tiers(client, db, reset_after):
    oh, h = company_id(db, "ocean-harvesting"), password_headers(client, db)
    client.put(f"/api/companies/{oh}/priorities", headers=h, json={"weights": {"testing_facilities": 3, "find_funding": 0}})
    tiers = [r["tier"] for r in client.get(f"/api/companies/{oh}/focus", headers=h).json()["top_three"]]
    order = {"high": 0, "medium": 1, "later": 2}
    assert tiers == sorted(tiers, key=order.__getitem__)
