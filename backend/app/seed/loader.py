"""Seeding: source registry, technologies, evidence-backed company profiles, source snapshots, demo reset."""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models import (
    CollaborationRecommendation,
    Company,
    CompanyAccount,
    CompanyClaim,
    CompanyPriority,
    CompanyTechnology,
    ProfileRevision,
    Recommendation,
    SavedRecommendation,
    Source,
    SourceHealth,
    Technology,
)
from app.services.collectors.base import SourceUnavailable, run_collector
from app.services.collectors.registry import SOURCES
from app.services.collectors.runner import get_collector
from app.services.collectors.store import upsert_evidence
from app.services.intelligence.taxonomy import TECHNOLOGIES

log = logging.getLogger("vsp.seed")
COMPANY_DIR = Path(__file__).resolve().parent / "companies"
# When the official-website excerpts in app/seed/companies were collected and verified verbatim.
COMPANY_EVIDENCE_RETRIEVED_AT = datetime.fromisoformat("2026-11-13T12:20:00+00:00")
SNAPSHOT_SOURCES = ("bsp_members", "vinnova", "bsp_news", "bsp_events")


def seed_sources(db: Session) -> None:
    for d in SOURCES:
        src = db.scalar(select(Source).where(Source.key == d.key))
        if src is None:
            src = Source(key=d.key)
            db.add(src)
        src.name, src.publisher, src.source_type, src.base_url = d.name, d.publisher, d.source_type, d.base_url
        src.description, src.license_note, src.allowed_hosts = d.description, d.license_note, list(d.allowed_hosts)
        src.enabled, src.collectable, src.llm_allowed, src.disabled_reason = d.enabled, d.collectable, d.llm_allowed, d.disabled_reason
        db.flush()
        if src.health is None:
            status = "disabled" if not d.enabled else ("not_applicable" if not d.collectable else "never_run")
            src.health = SourceHealth(source_id=src.id, status=status, data_mode="demo" if not d.collectable else "snapshot")
    db.flush()


def seed_technologies(db: Session) -> None:
    for t in TECHNOLOGIES:
        row = db.scalar(select(Technology).where(Technology.key == t.key))
        if row is None:
            row = Technology(key=t.key)
            db.add(row)
        row.name, row.area, row.description = t.label, t.area or "", t.description
        row.keywords = [term.removeprefix("CS:") for term in t.terms]
    db.flush()


def _company_files() -> list[dict]:
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(COMPANY_DIR.glob("*.json"))]


def seed_company(db: Session, data: dict) -> Company:
    web = db.scalar(select(Source).where(Source.key == "company_websites"))
    members = db.scalar(select(Source).where(Source.key == "bsp_members"))
    company = db.scalar(select(Company).where(Company.slug == data["slug"]))
    if company is None and data.get("membership"):
        company = db.scalar(select(Company).where(Company.bsp_member_id == data["membership"]["bsp_member_id"]))
    if company is None:
        company = Company(slug=data["slug"], name=data["name"])
        db.add(company)
    company.slug, company.name, company.legal_name = data["slug"], data["name"], data.get("legal_name")
    company.website, company.tagline = data.get("website"), data.get("tagline")
    company.profile_level, company.organisation_type = data["profile_level"], data.get("organisation_type", "company")
    company.is_demo_company = data.get("is_demo_company", False)
    db.flush()

    if m := data.get("membership"):
        ev = upsert_evidence(
            db, source=members, url=m["url"], title=f"{data['name']} — Blue Science Park member directory", publisher="Blue Science Park",
            excerpt=None, evidence_type="member_directory", provenance="snapshot", retrieved_at=COMPANY_EVIDENCE_RETRIEVED_AT,
            reuse_note="Membership listing (metadata only).",
        )
        company.bsp_member_id = m["bsp_member_id"]
        company.membership_status = "verified"
        company.membership_evidence_id = ev.id

    existing = {(c.field, c.value, c.claim_type): c for c in company.claims}
    for claim in data["claims"]:
        page = data["pages"][claim["page"]]
        ev = upsert_evidence(
            db, source=web, url=page["url"], title=page["title"], publisher=page["publisher"], excerpt=claim["excerpt"],
            evidence_type="official_website", provenance="snapshot", retrieved_at=COMPANY_EVIDENCE_RETRIEVED_AT,
            reuse_note="Short excerpt quoted to evidence a specific claim; see the original page for full context.",
        )
        if ev.verification_status == "not_checked":
            ev.verification_status = "verified"
            ev.verified_at = COMPANY_EVIDENCE_RETRIEVED_AT
        key = (claim["field"], claim["value"], "source_stated")
        if key not in existing:
            company.claims.append(CompanyClaim(
                field=claim["field"], value=claim["value"], label=claim.get("label"), claim_type="source_stated",
                status="active", evidence_id=ev.id,
            ))
    db.flush()
    return company


def seed_companies(db: Session) -> int:
    """Idempotent: adds missing companies and source-stated claims; never edits existing ones. Returns claims added."""
    before = db.scalar(select(func.count(CompanyClaim.id))) or 0
    for data in _company_files():
        seed_company(db, data)
    seed_accounts(db)
    return (db.scalar(select(func.count(CompanyClaim.id))) or 0) - before


def seed_accounts(db: Session) -> None:
    """One workspace login per profiled company (username = slug). Password from DEMO_COMPANY_PASSWORD or random."""
    import secrets

    from app.core.config import get_settings
    from app.security.auth import hash_password

    configured = get_settings().demo_company_password.get_secret_value()
    for company in db.scalars(select(Company).where(Company.profile_level.in_(("full", "partial")))):
        if db.scalar(select(CompanyAccount).where(CompanyAccount.company_id == company.id)) is None:
            db.add(CompanyAccount(company_id=company.id, username=company.slug,
                                  password_hash=hash_password(configured or secrets.token_urlsafe(18))))
    db.flush()


def retag_if_needed(db: Session) -> bool:
    """Backfill derived fields (e.g. geography) after a migration adds them. Returns True if anything changed."""
    from app.models import Opportunity
    from app.services.matching.tagging import tag_opportunity

    stale = list(db.scalars(select(Opportunity).where(Opportunity.geo_basis.is_(None))))
    for opp in stale:
        tag_opportunity(db, opp)
    if stale:
        db.commit()
    return bool(stale)


def load_snapshots(db: Session) -> None:
    for key in SNAPSHOT_SOURCES:
        collector = get_collector(key)
        try:
            collector.load_snapshot()
        except SourceUnavailable:
            log.warning(f"no snapshot for {key}; skipping")
            continue
        run_collector(db, collector, mode="snapshot", trigger="seed")


def is_seeded(db: Session) -> bool:
    return (db.scalar(select(func.count(Company.id)).where(Company.is_demo_company.is_(True))) or 0) > 0


def seed_all(db: Session, *, with_snapshots: bool = True, recompute: bool = True) -> None:
    from app.services.recommendations.pipeline import recompute_all

    seed_sources(db)
    seed_technologies(db)
    db.commit()
    seed_companies(db)
    db.commit()
    if with_snapshots:
        load_snapshots(db)
    if recompute:
        recompute_all(db)
    db.commit()


def reset_demo(db: Session) -> dict:
    """Return the workspace to a clean state. Collected source data is kept; user edits are removed."""
    profiled = list(db.scalars(select(Company).where(Company.profile_level.in_(("full", "partial")))))
    ids = [c.id for c in profiled]
    removed_user = db.execute(delete(CompanyClaim).where(CompanyClaim.company_id.in_(ids), CompanyClaim.claim_type != "source_stated")).rowcount
    for claim in db.scalars(select(CompanyClaim).where(CompanyClaim.company_id.in_(ids))):
        claim.status, claim.review_note, claim.reviewed_at, claim.superseded_by_id = "active", None, None, None
    db.execute(delete(ProfileRevision).where(ProfileRevision.company_id.in_(ids)))
    db.execute(delete(CompanyPriority).where(CompanyPriority.company_id.in_(ids)))
    db.execute(delete(SavedRecommendation).where(SavedRecommendation.company_id.in_(ids)))
    db.execute(delete(Recommendation).where(Recommendation.company_id.in_(ids)))
    db.execute(delete(CompanyTechnology).where(CompanyTechnology.company_id.in_(ids)))
    db.execute(delete(CollaborationRecommendation).where(CollaborationRecommendation.company_id.in_(ids)))
    db.flush()
    db.expire_all()
    seed_companies(db)  # restores any source-stated claims edited away
    db.commit()
    from app.services.recommendations.pipeline import recompute_all

    recompute_all(db)
    return {"companies_reset": len(ids), "user_and_inferred_claims_removed": removed_user}
