"""Profile refinement, review workflow, immutability of source facts, and company data isolation (reqs 12-14)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Company, CompanyClaim, CompanyTechnology, Recommendation
from app.models.company import SourceFactImmutableError
from app.services.intelligence.enrichment import run_inference
from app.services.recommendations.pipeline import Workspace
from tests.conftest import company_id


def _login(client, slug, db):
    r = client.post("/api/auth/demo-login", json={"company_id": company_id(db, slug)})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['token']}"}


def test_private_workspace_requires_that_companys_session(client, db):
    oh, cl = company_id(db, "ocean-harvesting"), company_id(db, "cleura")
    assert client.get(f"/api/companies/{oh}/recommendations").status_code == 401
    h = _login(client, "ocean-harvesting", db)
    assert client.get(f"/api/companies/{oh}/recommendations", headers=h).status_code == 200
    assert client.get(f"/api/companies/{cl}/recommendations", headers=h).status_code == 403
    assert client.get(f"/api/companies/{oh}/recommendations", headers={"Authorization": "Bearer forged.token"}).status_code == 401


def test_password_login_and_hashing(client, db):
    from app.models import CompanyAccount
    from app.security.auth import hash_password, verify_password

    stored = hash_password("correct horse")
    assert stored.startswith("pbkdf2_sha256$") and "correct horse" not in stored
    assert verify_password("correct horse", stored) and not verify_password("wrong", stored)
    acct = db.scalar(select(CompanyAccount).where(CompanyAccount.username == "roxtec"))
    acct.password_hash = hash_password("s3cret-pass")
    db.commit()
    assert client.post("/api/auth/login", json={"username": "roxtec", "password": "nope"}).status_code == 401
    ok = client.post("/api/auth/login", json={"username": "roxtec", "password": "s3cret-pass"})
    assert ok.status_code == 200 and ok.json()["company"]["slug"] == "roxtec"


def test_profile_refinement_changes_recommendations(client, db, reset_after):
    oh = company_id(db, "ocean-harvesting")
    h = _login(client, "ocean-harvesting", db)
    r = client.put(f"/api/companies/{oh}/priorities", headers=h, json={"weights": {"testing_facilities": 3, "find_funding": 0}})
    assert r.status_code == 200
    changes = r.json()["ranking_changes"]
    assert changes, "changing priorities must change the ranking"
    moved_up = [c for c in changes if c["change"] == "up"]
    assert any("test" in c["title"].lower() or "Kiwa" in c["title"] for c in moved_up)


def test_rejecting_inferred_interest_removes_its_influence(client, db, reset_after):
    oh = company_id(db, "ocean-harvesting")
    h = _login(client, "ocean-harvesting", db)
    claim = db.scalar(select(CompanyClaim).where(CompanyClaim.company_id == oh, CompanyClaim.inference_rule == "digital_twin_interest"))
    assert claim is not None and claim.claim_type == "inferred"
    before = db.scalar(select(CompanyTechnology).join(CompanyTechnology.technology).where(
        CompanyTechnology.company_id == oh, CompanyTechnology.technology.has(key="digital_twins")))
    score_before = before.score
    assert claim.id in [c["id"] for c in before.detail["interest_claims"]]
    r = client.post(f"/api/companies/{oh}/claims/{claim.id}/review", headers=h, json={"action": "reject"})
    assert r.status_code == 200 and r.json()["claim"]["influences_matching"] is False
    db.expire_all()
    after = db.scalar(select(CompanyTechnology).join(CompanyTechnology.technology).where(
        CompanyTechnology.company_id == oh, CompanyTechnology.technology.has(key="digital_twins")))
    assert after.score < score_before
    assert claim.id not in [c["id"] for c in after.detail["interest_claims"]]
    for rec in db.scalars(select(Recommendation).where(Recommendation.company_id == oh, Recommendation.is_current.is_(True))):
        assert claim.id not in rec.detail.get("claim_ids", [])
    # A rejected inference is not silently re-created on recompute.
    company = db.get(Company, oh)
    outcome = next(o for o in run_inference(db, company, dry_run=True) if o.rule == "digital_twin_interest")
    assert outcome.status == "skipped_rejected_by_user"


def test_source_stated_facts_cannot_be_silently_overwritten(seeded, db):
    claim = db.scalar(select(CompanyClaim).where(CompanyClaim.claim_type == "source_stated"))
    claim.value = "Overwritten by an inference"
    with pytest.raises(SourceFactImmutableError):
        db.flush()
    db.rollback()
    claim = db.scalar(select(CompanyClaim).where(CompanyClaim.claim_type == "source_stated"))
    claim.claim_type = "inferred"
    with pytest.raises(SourceFactImmutableError):
        db.flush()
    db.rollback()


def test_inference_is_skipped_when_source_facts_already_cover_it(seeded, db):
    cleura = db.get(Company, company_id(db, "cleura"))
    outcomes = {o.rule: o for o in run_inference(db, cleura, dry_run=True)}
    assert outcomes["defence_market_interest"].status == "skipped_covered_by_source"


def test_correction_supersedes_but_preserves_the_source_fact(client, db, reset_after):
    oh = company_id(db, "ocean-harvesting")
    h = _login(client, "ocean-harvesting", db)
    stated = db.scalar(select(CompanyClaim).where(CompanyClaim.company_id == oh, CompanyClaim.field == "product"))
    original = stated.value
    r = client.patch(f"/api/companies/{oh}/profile", headers=h,
                     json={"corrections": [{"claim_id": stated.id, "value": "InfinityWEC generation 8 (company update)"}]})
    assert r.status_code == 200
    db.expire_all()
    stated = db.get(CompanyClaim, stated.id)
    assert stated.value == original and stated.status == "corrected" and stated.superseded_by_id
    assert db.get(CompanyClaim, stated.superseded_by_id).claim_type == "user_provided"
    rejected = client.post(f"/api/companies/{oh}/claims/{stated.id}/review", headers=h, json={"action": "reject"})
    assert rejected.status_code == 409


def test_private_edits_never_leak_to_other_companies(client, db, reset_after):
    oh, rox = company_id(db, "ocean-harvesting"), company_id(db, "roxtec")
    h = _login(client, "ocean-harvesting", db)
    secret = "Confidential plan: acquire a robotics start-up for autonomous drone inspection"
    assert client.patch(f"/api/companies/{oh}/profile", headers=h,
                        json={"add_claims": [{"field": "business_focus", "value": secret}]}).status_code == 200
    # Other companies and anonymous users never see the private claim ...
    public = client.get(f"/api/companies/{oh}/claims").json()
    assert all(secret not in c["value"] for c in public)
    hr = _login(client, "roxtec", db)
    assert all(secret not in c["value"] for c in client.get(f"/api/companies/{oh}/claims", headers=hr).json())
    # ... and it does not influence another company's results.
    ws = Workspace(db)
    partner_view = ws.profile(oh, public=True)
    assert "robotics" not in partner_view.concepts
    assert "robotics" in ws.profile(oh).concepts
    rox_collab = client.get(f"/api/companies/{rox}/collaborations", headers=hr).json()
    assert secret not in str(rox_collab)


def test_search_history_is_company_specific(client, db):
    h = _login(client, "cleura", db)
    client.get("/api/search", params={"q": "Which research opportunities should Cleura explore?"}, headers=h)
    mine = client.get("/api/search/history", headers=h).json()
    assert mine and mine[0]["query"].startswith("Which research")
    other = client.get("/api/search/history", headers=_login(client, "roxtec", db)).json()
    assert all("Cleura" not in x["query"] for x in other)
    assert client.get("/api/search/history").status_code == 401
