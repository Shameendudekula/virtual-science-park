"""ORM -> API dict conversion helpers."""
from __future__ import annotations

from app.models import Company, CompanyClaim, Evidence, Opportunity, Recommendation
from app.schemas.api import ClaimOut, CompanySummary, EvidenceOut
from app.services.intelligence.profile import claim_concepts, claim_strength
from app.services.matching.opportunity_matching import MatchResult, timeliness
from app.core.clock import today

CATEGORY_LABELS = {
    "funding_call": "Funding call", "research_funding": "Research funding", "innovation_programme": "Innovation programme",
    "business_programme": "Business programme", "event": "Event", "testing_facility": "Testing & test environments",
    "research_collaboration": "Research collaboration", "ecosystem_news": "Ecosystem news",
}


def evidence_out(e: Evidence | None) -> dict | None:
    if e is None:
        return None
    d = EvidenceOut.model_validate(e).model_dump(mode="json")
    d["source_key"] = e.source.key if e.source else None
    return d


def claim_out(c: CompanyClaim) -> dict:
    d = ClaimOut.model_validate(c).model_dump(mode="json")
    d["concepts"] = sorted(claim_concepts(c).keys())
    d["influences_matching"] = claim_strength(c) > 0
    d["evidence"] = evidence_out(c.evidence)
    return d


def company_summary(c: Company) -> dict:
    return CompanySummary.model_validate(c).model_dump(mode="json")


def opportunity_out(o: Opportunity, match: MatchResult | None = None) -> dict:
    d = {
        "id": o.id, "external_id": o.external_id, "title": o.title, "title_original": o.title_original,
        "description": o.description, "purpose_text": o.purpose_text, "eligibility_text": o.eligibility_text,
        "funding_text": o.funding_text, "category": o.category, "category_label": CATEGORY_LABELS.get(o.category, o.category),
        "organisation": o.organisation, "programme": o.programme, "source_key": o.source.key if o.source else None,
        "source_name": o.source.name if o.source else None, "source_url": o.source_url, "apply_url": o.apply_url,
        "language": o.language,
        "published_at": o.published_at.isoformat() if o.published_at else None,
        "opens_at": o.opens_at.isoformat() if o.opens_at else None,
        "deadline_at": o.deadline_at.isoformat() if o.deadline_at else None,
        "deadline_status": o.deadline_status, "rolling_assessment": o.rolling_assessment,
        "decision_expected_at": o.decision_expected_at.isoformat() if o.decision_expected_at else None,
        "provenance": o.provenance, "retrieved_at": o.retrieved_at.isoformat(), "quality_flags": o.quality_flags,
        "concepts": [{"key": k, **v} for k, v in (o.concepts or {}).items()],
        "geo_scopes": o.geo_scopes, "geo_basis": o.geo_basis, "geo_inferred": o.geo_inferred,
        "event_format": o.event_format, "format_basis": o.format_basis,
        "evidence_id": o.evidence_id,
        "timeliness": timeliness(o, today()),
    }
    if match is not None:
        d["match"] = match.as_dict()
    return d


def recommendation_out(r: Recommendation) -> dict:
    return {
        "id": r.id, "company_id": r.company_id, "fingerprint": r.fingerprint, "kind": r.kind, "title": r.title,
        "priority_tier": r.priority_tier, "rank_score": r.rank_score, "rank_position": r.rank_position,
        "status": r.status, "status_changed_at": r.status_changed_at.isoformat() if r.status_changed_at else None,
        "related_opportunity_id": r.related_opportunity_id, "related_company_id": r.related_company_id,
        "related_technology_id": r.related_technology_id, "computed_at": r.computed_at.isoformat(), "detail": r.detail,
    }
