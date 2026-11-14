"""Concept tagging of opportunities (which concepts an opportunity is about, and where that came from)."""
from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import Opportunity, OpportunityTechnology, Technology
from app.services.intelligence.concepts import extract
from app.services.intelligence.geography import opportunity_geo
from app.services.intelligence.taxonomy import TECHNOLOGY_KEYS

# Weight of a concept depending on where in the opportunity it was found.
FIELD_WEIGHTS = (("title", 1.0), ("purpose_text", 0.85), ("description", 0.8), ("programme", 0.5))


def opportunity_concepts(opp: Opportunity) -> dict[str, dict]:
    """Eligibility and funding texts are excluded on purpose: they describe who may apply, not the topic."""
    result: dict[str, dict] = {}
    for field_name, weight in FIELD_WEIGHTS:
        for key, match in extract(getattr(opp, field_name)).items():
            w = weight if match.direct else weight * 0.6
            current = result.get(key)
            if current is None or w > current["weight"]:
                result[key] = {
                    "weight": round(w, 3),
                    "field": field_name,
                    "terms": match.terms[:4],
                    "direct": match.direct,
                }
    return result


def tag_geography(opp: Opportunity) -> None:
    geo = opportunity_geo(organisation=opp.organisation, category=opp.category, title=opp.title,
                          text="\n".join(t for t in (opp.description, opp.purpose_text, opp.programme) if t))
    opp.geo_scopes, opp.geo_basis, opp.geo_inferred = geo.scopes, geo.basis, geo.inferred
    opp.event_format, opp.format_basis = geo.event_format, geo.format_basis


def tag_opportunity(db: Session, opp: Opportunity) -> None:
    opp.concepts = opportunity_concepts(opp)
    tag_geography(opp)
    db.execute(delete(OpportunityTechnology).where(OpportunityTechnology.opportunity_id == opp.id))
    tech_ids = {t.key: t.id for t in db.scalars(select(Technology))}
    for key, info in opp.concepts.items():
        if key in TECHNOLOGY_KEYS and key in tech_ids and info["direct"]:
            db.add(OpportunityTechnology(opportunity_id=opp.id, technology_id=tech_ids[key], matched_terms=info["terms"]))
    db.flush()
