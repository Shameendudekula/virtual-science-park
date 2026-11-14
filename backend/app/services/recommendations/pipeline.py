"""Recompute pipeline: profile -> opportunities -> technologies -> collaborations -> recommendations."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session, selectinload

from app.core.clock import today, utcnow
from app.models import (
    CollaborationRecommendation,
    Company,
    CompanyTechnology,
    Opportunity,
    Recommendation,
    Technology,
)
from app.services.intelligence.enrichment import run_inference
from app.services.intelligence.profile import CompanyProfileModel, build_profile, ensure_priorities
from app.services.matching.complementarity import CollaborationResult, assess_pair, collaboration_detail
from app.services.matching.opportunity_matching import RELEVANT_THRESHOLD, MatchResult, score_opportunity
from app.services.matching.technology_relevance import TechRelevance, assess_technologies
from app.services.recommendations.engine import (
    consortium_candidates,
    executive_summary,
    opportunity_candidates,
    partner_candidates,
    rank,
    technology_candidates,
)

log = logging.getLogger("vsp.pipeline")
PROFILED_LEVELS = ("full", "partial")


@dataclass
class Intelligence:
    profile: CompanyProfileModel
    matches: list[tuple[Opportunity, MatchResult]]
    technologies: list[TechRelevance]
    collaborations: list[CollaborationResult]


def active_opportunities(db: Session) -> list[Opportunity]:
    return list(db.scalars(select(Opportunity).where(Opportunity.is_active.is_(True)).order_by(Opportunity.id)))


def profiled_companies(db: Session) -> list[Company]:
    return list(db.scalars(
        select(Company).options(selectinload(Company.claims), selectinload(Company.priorities))
        .where(Company.profile_level.in_(PROFILED_LEVELS)).order_by(Company.id)
    ))


def match_all(profile: CompanyProfileModel, opps: list[Opportunity]) -> list[tuple[Opportunity, MatchResult]]:
    d = today()
    results = [(o, score_opportunity(profile, o, d)) for o in opps]
    results.sort(key=lambda om: (-om[1].score, om[0].id))
    return results


class Workspace:
    """Profiles and opportunity matches for every profiled company, built once per recompute.

    Data isolation: a company's own results use its private profile (its edits, reviews and priorities);
    every *other* company is seen only through its public profile (source facts + rule inferences).
    """

    def __init__(self, db: Session) -> None:
        self.companies = profiled_companies(db)
        self.opps = active_opportunities(db)
        self.opp_by_id = {o.id: o for o in self.opps}
        self.profiles: dict[int, CompanyProfileModel] = {c.id: build_profile(c) for c in self.companies}
        self.public_profiles: dict[int, CompanyProfileModel] = {c.id: build_profile(c, public=True) for c in self.companies}
        self._matches: dict[tuple[int, bool], list[tuple[Opportunity, MatchResult]]] = {}

    def profile(self, company_id: int, public: bool = False) -> CompanyProfileModel:
        return (self.public_profiles if public else self.profiles)[company_id]

    def matches(self, company_id: int, public: bool = False) -> list[tuple[Opportunity, MatchResult]]:
        key = (company_id, public)
        if key not in self._matches:
            self._matches[key] = match_all(self.profile(company_id, public), self.opps)
        return self._matches[key]

    def match_map(self, company_id: int, public: bool = False) -> dict[int, MatchResult]:
        return {o.id: m for o, m in self.matches(company_id, public)}

    def intelligence(self, company_id: int) -> Intelligence:
        profile = self.profiles[company_id]
        matches = self.matches(company_id)
        techs = assess_technologies(profile, matches)
        own = self.match_map(company_id)
        collabs: list[CollaborationResult] = []
        for other_id, other_profile in self.public_profiles.items():
            if other_id == company_id:
                continue
            result = assess_pair(profile, other_profile, own, self.match_map(other_id, public=True), self.opp_by_id)
            if result:
                collabs.append(result)
        collabs.sort(key=lambda r: (-r.score, r.partner.company.id))
        return Intelligence(profile, matches, techs, collabs)


def prepare(db: Session) -> None:
    """Phase 1: priorities and rule-based enrichment for every profiled company (before any matching)."""
    for company in profiled_companies(db):
        ensure_priorities(db, company)
        run_inference(db, company)
    db.flush()
    db.expire_all()


def compute(db: Session, company: Company) -> Intelligence:
    """Read-only computation for one company (used by API views)."""
    return Workspace(db).intelligence(company.id)


def persist(db: Session, ws: Workspace, company_id: int) -> dict:
    intel = ws.intelligence(company_id)
    company = intel.profile.company
    now = utcnow()

    tech_ids = {t.key: t.id for t in db.scalars(select(Technology))}
    db.execute(delete(CompanyTechnology).where(CompanyTechnology.company_id == company.id))
    for t in intel.technologies:
        if t.key in tech_ids:
            db.add(CompanyTechnology(company_id=company.id, technology_id=tech_ids[t.key], relation=t.relation, ring=t.ring,
                                     score=round(t.score, 2), detail=t.as_dict(), computed_at=now))

    db.execute(delete(CollaborationRecommendation).where(CollaborationRecommendation.company_id == company.id))
    for r in intel.collaborations:
        db.add(CollaborationRecommendation(company_id=company.id, partner_id=r.partner.company.id, score=round(r.score, 2),
                                           strength=r.strength, detail=collaboration_detail(intel.profile, r), computed_at=now))

    match_by_id = {o.id: m for o, m in intel.matches}
    candidates = (
        opportunity_candidates(intel.profile, intel.matches)
        + technology_candidates(intel.profile, intel.technologies)
        + partner_candidates(intel.profile, intel.collaborations)
        + consortium_candidates(intel.profile, match_by_id, ws.opp_by_id, intel.collaborations)
    )
    ranked = rank(intel.profile, candidates)

    existing = {r.fingerprint: r for r in db.scalars(select(Recommendation).where(Recommendation.company_id == company.id))}
    db.execute(update(Recommendation).where(Recommendation.company_id == company.id).values(is_current=False))
    for position, c in enumerate(ranked, start=1):
        c.detail["criteria"] = c.criteria
        c.detail["summary"] = c.summary
        rec = existing.get(c.fingerprint)
        if rec is None:
            rec = Recommendation(company_id=company.id, fingerprint=c.fingerprint, status="open")
            db.add(rec)
        rec.kind = c.kind
        rec.title = c.title[:400]
        rec.priority_tier = c.tier
        rec.rank_score = round(c.rank, 2)
        rec.rank_position = position
        rec.detail = c.detail
        rec.related_opportunity_id = c.related_opportunity_id
        rec.related_company_id = c.related_company_id
        rec.related_technology_id = tech_ids.get(c.related_technology_key) if c.related_technology_key else None
        rec.is_current = True
        rec.computed_at = now
    db.flush()
    return {"company_id": company.id, "recommendations": len(ranked)}


def summary_for(ws: Workspace, company_id: int) -> dict:
    intel = ws.intelligence(company_id)
    candidates = (
        opportunity_candidates(intel.profile, intel.matches)
        + technology_candidates(intel.profile, intel.technologies)
        + partner_candidates(intel.profile, intel.collaborations)
        + consortium_candidates(intel.profile, ws.match_map(company_id), ws.opp_by_id, intel.collaborations)
    )
    ranked = rank(intel.profile, candidates)
    relevant = sum(1 for _o, m in intel.matches if m.score >= RELEVANT_THRESHOLD and m.is_actionable)
    return executive_summary(intel.profile, ranked, intel.technologies, intel.collaborations, relevant, today())


def recompute_all(db: Session) -> None:
    prepare(db)
    ws = Workspace(db)
    for company in ws.companies:
        persist(db, ws, company.id)
    db.commit()
    log.info(f"recomputed intelligence for {len(ws.companies)} companies over {len(ws.opps)} opportunities")


def ranking_snapshot(db: Session, company_id: int) -> dict[str, dict]:
    rows = db.scalars(select(Recommendation).where(Recommendation.company_id == company_id, Recommendation.is_current.is_(True)))
    return {r.fingerprint: {"id": r.id, "title": r.title, "position": r.rank_position, "tier": r.priority_tier, "score": r.rank_score} for r in rows}


def ranking_diff(before: dict[str, dict], after: dict[str, dict]) -> list[dict]:
    changes = []
    for fp, a in after.items():
        b = before.get(fp)
        if b is None:
            changes.append({"fingerprint": fp, "id": a["id"], "title": a["title"], "change": "new", "before": None, "after": a})
        elif b["position"] != a["position"] or b["tier"] != a["tier"]:
            changes.append({"fingerprint": fp, "id": a["id"], "title": a["title"],
                            "change": "up" if a["position"] < b["position"] else ("down" if a["position"] > b["position"] else "tier"),
                            "before": b, "after": a})
    for fp, b in before.items():
        if fp not in after:
            changes.append({"fingerprint": fp, "id": b["id"], "title": b["title"], "change": "removed", "before": b, "after": None})
    changes.sort(key=lambda c: (c["after"] or {"position": 999})["position"])
    return changes
