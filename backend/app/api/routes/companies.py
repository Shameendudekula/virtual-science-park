"""Company-centric endpoints: profile, review workflow, the five stages, comparison and the brief."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.serializers import claim_out, company_summary, evidence_out, opportunity_out, recommendation_out
from app.db.session import get_db
from app.models import CollaborationRecommendation, Company, CompanyClaim, CompanyTechnology, ProfileRevision, Recommendation
from app.schemas.api import ClaimReview, CompanySummary, Page, PrioritiesUpdate, ProfilePatch
from app.security.auth import Principal, PrincipalDep, require_company, require_company_write
from app.security.deps import rate_limit, write_rate_limit
from app.services.intelligence import editing
from app.services.intelligence.enrichment import run_inference
from app.services.intelligence.profile import build_profile, claim_strength_public, load_company
from app.services.intelligence.taxonomy import ALL_CONCEPTS, PRIORITIES, RADAR_AREAS
from app.services.intelligence.views import compare, completeness, graph, innovation_brief, overview
from app.services.matching.opportunity_matching import RELEVANT_THRESHOLD
from app.services.recommendations.pipeline import Workspace, ranking_diff, ranking_snapshot, recompute_all

router = APIRouter(prefix="/api/companies", tags=["companies"])
_WRITE_LIMIT = Depends(write_rate_limit(30, 60))  # each change recomputes rankings; refused attempts use a separate bucket


def _company(db: Session, company_id: int, *, profiled: bool = False) -> Company:
    company = load_company(db, company_id)
    if company is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Company {company_id} not found")
    if profiled and company.profile_level not in ("full", "partial"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                            f"{company.name} is listed in the member directory but has no VSP profile yet, so no intelligence can be computed.")
    return company


@router.get("", response_model=Page[CompanySummary], summary="List and search companies")
def list_companies(
    q: str | None = Query(default=None, max_length=100), profile_level: str | None = Query(default=None, pattern="^(full|partial|directory|profiled)$"),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db),
) -> dict:
    stmt = select(Company)
    if q:
        stmt = stmt.where(or_(Company.name.ilike(f"%{q}%"), Company.slug.ilike(f"%{q}%")))
    if profile_level == "profiled":
        stmt = stmt.where(Company.profile_level.in_(("full", "partial")))
    elif profile_level:
        stmt = stmt.where(Company.profile_level == profile_level)
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    order = [Company.is_demo_company.desc(), Company.profile_level, Company.name]
    rows = db.scalars(stmt.order_by(*order).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [company_summary(c) for c in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/compare", summary="Compare two profiled companies")
def compare_companies(a: int = Query(...), b: int = Query(...), db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    if a == b:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Choose two different companies to compare.")
    _company(db, a, profiled=True)
    _company(db, b, profiled=True)
    return compare(Workspace(db), a, b, viewer_id=principal.company_id)


@router.get("/{company_id}", summary="Company detail (public facts; private stats only for the company's own workspace)")
def get_company(company_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    c = _company(db, company_id)
    p = build_profile(c, public=not principal.can_access(company_id))
    claims = p.effective_claims
    d = company_summary(c)
    d.update({
        "legal_name": c.legal_name,
        "membership_evidence": evidence_out(c.membership_evidence),
        "overview": next((x.value for x in claims if x.field == "overview"), None),
        "stats": {
            "claims": len(claims),
            "source_stated": sum(1 for x in claims if x.claim_type == "source_stated"),
            "inferred": sum(1 for x in claims if x.claim_type == "inferred"),
            "user_provided": sum(1 for x in claims if x.claim_type == "user_provided"),
            "completeness_pct": completeness(p)["score_pct"] if c.profile_level != "directory" else 0,
        },
        "location": p.geo.as_dict() if p.geo else None,
        "view": "public" if p.public else "private",
    })
    return d


@router.get("/{company_id}/overview", summary="Overview dashboard for a company")
def company_overview(company_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    return overview(db, Workspace(db), company_id)


@router.get("/{company_id}/profile", summary="Evidence-backed company profile")
def get_profile(company_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company(company_id, principal)
    c = _company(db, company_id, profiled=True)
    p = build_profile(c)
    groups: dict[str, list[dict]] = {}
    for claim in sorted(c.claims, key=lambda x: (x.field, {"source_stated": 0, "user_provided": 1, "inferred": 2}[x.claim_type], x.id)):
        groups.setdefault(claim.field, []).append(claim_out(claim))
    concepts = [
        {"key": k, "label": ALL_CONCEPTS[k].label, "kind": ALL_CONCEPTS[k].kind, "strength": round(s.strength, 2),
         "interest_only": s.via_interest_only, "claim_ids": [x.id for x in s.claims[:4]]}
        for k, s in sorted(p.concepts.items(), key=lambda kv: (-kv[1].strength, kv[0]))
    ]
    revisions = db.scalars(select(ProfileRevision).where(ProfileRevision.company_id == company_id).order_by(ProfileRevision.created_at.desc()).limit(25))
    return {
        "company": get_company(company_id, db, principal),
        "groups": groups,
        "concepts": concepts,
        "completeness": completeness(p),
        "priorities": [{"key": k, **PRIORITIES[k], "weight": p.priorities.get(k, 1)} for k in PRIORITIES],
        "inference_rules": [o.__dict__ for o in run_inference(db, c, dry_run=True)],
        "revisions": [{"id": r.id, "action": r.action, "claim_id": r.claim_id, "before": r.before, "after": r.after, "note": r.note,
                       "created_at": r.created_at.isoformat()} for r in revisions],
        "legend": {
            "source_stated": "Fact stated in a cited public source (excerpt shown).",
            "inferred": "Rule-based inference — not a verified fact. Confirm or reject it.",
            "user_provided": "Entered by a company representative in VSP.",
            "unknown": "Not found in collected sources.",
        },
    }


def _apply_and_diff(db: Session, company: Company, mutate) -> dict:  # noqa: ANN001
    before = ranking_snapshot(db, company.id)
    result = mutate()
    db.flush()
    recompute_all(db)
    after = ranking_snapshot(db, company.id)
    return {"result": result, "ranking_changes": ranking_diff(before, after)}


@router.patch("/{company_id}/profile", summary="Refine a profile: add claims, correct claims, set priorities",
              dependencies=[_WRITE_LIMIT])
def patch_profile(company_id: int, body: ProfilePatch, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company_write(company_id, principal)
    c = _company(db, company_id, profiled=not principal.is_admin)
    if c.profile_level == "directory":
        if body.corrections or not body.add_claims:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "A directory-only member can only be given new user-provided claims.")
        c.profile_level = "partial"  # labelled: profile built from user-provided information only

    def mutate() -> dict:
        added, corrected = [], []
        for nc in body.add_claims:
            added.append(editing.add_claim(db, c, nc.field, nc.value, nc.label).id)
        for corr in body.corrections:
            claim = db.get(CompanyClaim, corr.claim_id)
            if claim is None or claim.company_id != c.id:
                raise HTTPException(status.HTTP_404_NOT_FOUND, f"Claim {corr.claim_id} not found for this company")
            corrected.append(editing.correct_claim(db, c, claim, corr.value, corr.label, corr.note).id)
        prios = editing.set_priorities(db, c, body.priorities) if body.priorities else None
        return {"added_claim_ids": added, "correction_claim_ids": corrected, "priorities": prios}

    out = _apply_and_diff(db, c, mutate)
    db.expire_all()
    out["profile"] = get_profile(company_id, db, principal)
    return out


@router.get("/{company_id}/claims", summary="All claims (facts, inferences and user input) for a company")
def list_claims(company_id: int, claim_type: str | None = Query(default=None, pattern="^(source_stated|inferred|user_provided)$"),
                db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> list[dict]:
    c = _company(db, company_id)
    rows = [x for x in sorted(c.claims, key=lambda x: x.id) if claim_type is None or x.claim_type == claim_type]
    if principal.can_access(company_id):
        return [claim_out(x) for x in rows]
    user_ids = {x.id for x in c.claims if x.claim_type == "user_provided"}
    public = []
    for x in rows:
        if claim_strength_public(x, user_ids) > 0:
            d = claim_out(x)
            d.update({"status": "active", "review_note": None, "reviewed_at": None, "superseded_by_id": None, "influences_matching": True})
            public.append(d)
    return public


@router.post("/{company_id}/claims/{claim_id}/review", summary="Confirm, reject, mark outdated or restore a claim",
             dependencies=[_WRITE_LIMIT])
def review_claim(company_id: int, claim_id: int, body: ClaimReview, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company_write(company_id, principal)
    c = _company(db, company_id, profiled=True)
    claim = db.get(CompanyClaim, claim_id)
    if claim is None or claim.company_id != c.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Claim {claim_id} not found for this company")
    try:
        out = _apply_and_diff(db, c, lambda: claim_out(editing.review_claim(db, c, claim, body.action, body.note)))
    except editing.ReviewNotAllowed as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.refresh(claim)
    out["claim"] = claim_out(claim)
    return out


@router.put("/{company_id}/priorities", summary="Set company priorities and see how rankings change", dependencies=[_WRITE_LIMIT])
def put_priorities(company_id: int, body: PrioritiesUpdate, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company_write(company_id, principal)
    c = _company(db, company_id, profiled=True)
    return _apply_and_diff(db, c, lambda: editing.set_priorities(db, c, body.weights))


@router.get("/{company_id}/opportunities", summary="Opportunities ranked for a company, with match explanations")
def company_opportunities(
    company_id: int,
    category: list[str] | None = Query(default=None), technology: str | None = None, industry: str | None = None,
    source: str | None = None, min_score: int = Query(0, ge=0, le=100), q: str | None = Query(default=None, max_length=100),
    deadline_before: datetime | None = None, include_closed: bool = False, include_news: bool = False,
    region: str | None = Query(default=None, pattern="^(karlskrona|blekinge|sweden|europe|international|online)$"),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db),
    principal: Principal = PrincipalDep,
) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    ws = Workspace(db)
    items = []
    for opp, m in ws.matches(company_id):
        if category and opp.category not in category:
            continue
        if not include_news and opp.category == "ecosystem_news" and not (category and "ecosystem_news" in category):
            continue
        if not include_closed and m.timeliness["status"] == "closed":
            continue
        if m.score < min_score:
            continue
        if technology and technology not in (opp.concepts or {}):
            continue
        if industry and industry not in (opp.concepts or {}):
            continue
        if source and (opp.source.key if opp.source else None) != source:
            continue
        if q and q.lower() not in (opp.title + " " + (opp.description or "") + " " + (opp.programme or "")).lower():
            continue
        if deadline_before and (opp.deadline_at is None or opp.deadline_at > deadline_before):
            continue
        if region and region not in (opp.geo_scopes or []):
            continue
        items.append(opportunity_out(opp, m))
    total = len(items)
    facets = {
        "categories": sorted({o.category for o, _ in ws.matches(company_id)}),
        "sources": sorted({o.source.key for o, _ in ws.matches(company_id) if o.source}),
        "technologies": sorted({k for o, _ in ws.matches(company_id) for k in (o.concepts or {}) if ALL_CONCEPTS.get(k) and ALL_CONCEPTS[k].kind == "technology"}),
        "industries": sorted({k for o, _ in ws.matches(company_id) for k in (o.concepts or {}) if ALL_CONCEPTS.get(k) and ALL_CONCEPTS[k].kind == "domain"}),
    }
    start = (page - 1) * page_size
    return {"items": items[start:start + page_size], "total": total, "page": page, "page_size": page_size,
            "relevant_threshold": RELEVANT_THRESHOLD, "facets": facets}


@router.get("/{company_id}/technologies", summary="Technology radar for a company")
def company_technologies(company_id: int, area: str | None = None, industry: str | None = None, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    rows = db.execute(select(CompanyTechnology).where(CompanyTechnology.company_id == company_id)).scalars().all()
    items = [r.detail for r in rows]
    if area:
        items = [i for i in items if i["area"] == area]
    if industry:
        items = [i for i in items if any(industry.lower() in c["explanation"].lower() for c in i["contributions"])]
    others = db.execute(
        select(CompanyTechnology, Company).join(Company, Company.id == CompanyTechnology.company_id)
        .where(CompanyTechnology.company_id != company_id, CompanyTechnology.relation.in_(("core", "adjacent")))
    ).all()
    related: dict[str, list[dict]] = {}
    for ct, comp in others:
        related.setdefault(ct.detail["key"], []).append({"id": comp.id, "name": comp.name, "relation": ct.relation})
    for i in items:
        i["related_companies"] = related.get(i["key"], [])[:4]
    order = {"adopt": 0, "trial": 1, "assess": 2, "monitor": 3}
    items.sort(key=lambda i: (order[i["ring"]], -i["score"]))
    return {"items": items, "areas": list(RADAR_AREAS), "rings": ["adopt", "trial", "assess", "monitor"],
            "ring_definitions": {
                "adopt": "Act now: documented capability link, open relevant opportunities, high score.",
                "trial": "Run a pilot or experiment: documented capability link or recorded interest.",
                "assess": "Investigate: plausible link with limited evidence.",
                "monitor": "Watch: industry-level relevance only.",
            },
            "note": "Rings are VSP recommendations of attention for this company, not objective technology maturity levels."}


@router.get("/{company_id}/collaborations", summary="Potential collaboration partners (complementarity-based)")
def company_collaborations(company_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    rows = db.scalars(select(CollaborationRecommendation).where(CollaborationRecommendation.company_id == company_id)
                      .order_by(CollaborationRecommendation.score.desc())).all()
    return {"items": [{"id": r.id, "partner_id": r.partner_id, "score": r.score, "strength": r.strength, **r.detail} for r in rows],
            "method": "Suggestions require at least one complementarity rule (a documented need on one side and a documented offer on the other). "
                      "Shared industries or keywords alone never create a suggestion."}


@router.get("/{company_id}/graph", summary="Collaboration / ecosystem graph around a company")
def company_graph(company_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    return graph(Workspace(db), company_id)


@router.get("/{company_id}/recommendations", summary="Prioritised, explainable recommendations")
def company_recommendations(
    company_id: int, tier: str | None = Query(default=None, pattern="^(high|medium|later)$"),
    status_filter: str | None = Query(default=None, alias="status", pattern="^(open|saved|dismissed|explored)$"),
    kind: str | None = None, db: Session = Depends(get_db), principal: Principal = PrincipalDep,
) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    stmt = select(Recommendation).where(Recommendation.company_id == company_id, Recommendation.is_current.is_(True))
    if tier:
        stmt = stmt.where(Recommendation.priority_tier == tier)
    if status_filter:
        stmt = stmt.where(Recommendation.status == status_filter)
    if kind:
        stmt = stmt.where(Recommendation.kind == kind)
    rows = db.scalars(stmt.order_by(Recommendation.rank_position)).all()
    from app.services.llm.adapter import polish_summary
    from app.services.recommendations.pipeline import summary_for

    return {"items": [recommendation_out(r) for r in rows], "summary": polish_summary(summary_for(Workspace(db), company_id)),
            "method": {
                "ranking": "Rank = stage relevance (40) + priority alignment (25) + urgency (15) + evidence strength (10) + actionability (10).",
                "tiers": {"high": "Rank ≥ 55, evidence strength ≥ 6, not based only on unconfirmed inferences.", "medium": "Rank ≥ 42.",
                          "later": "Rank < 42."},
            }}


@router.get("/{company_id}/innovation-brief", summary="Innovation brief (JSON or PDF)",
            responses={200: {"content": {"application/pdf": {}}}},
            dependencies=[Depends(rate_limit("brief", 20, 60))])
def company_brief(company_id: int, format: str = Query("json", pattern="^(json|pdf)$"), db: Session = Depends(get_db), principal: Principal = PrincipalDep):  # noqa: A002, ANN201
    require_company(company_id, principal)
    c = _company(db, company_id, profiled=True)
    brief = innovation_brief(db, Workspace(db), company_id)
    if format == "pdf":
        from app.services.intelligence.brief_pdf import render_pdf

        return Response(render_pdf(brief), media_type="application/pdf",
                        headers={"Content-Disposition": f'attachment; filename="innovation-brief-{c.slug}.pdf"'})
    return brief


@router.get("/{company_id}/focus", summary="Your Innovation Opportunities — compact view for small companies")
def company_focus(company_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    from app.services.intelligence.views import focus

    return focus(db, Workspace(db), company_id)


@router.get("/{company_id}/funding", summary="Unified funding discovery across supported sources")
def company_funding(company_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    require_company(company_id, principal)
    _company(db, company_id, profiled=True)
    from app.services.intelligence.views import funding_discovery

    return funding_discovery(db, Workspace(db), company_id)
