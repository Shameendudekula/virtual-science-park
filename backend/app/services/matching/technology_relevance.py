"""Technology relevance: why each radar technology matters (or not) to a company, with ring rules.

Rings are *recommendations of attention*, not objective maturity levels:
  adopt   — act now: documented capability link AND relevant open opportunities AND high score
  trial   — run an experiment or pilot: documented capability link or confirmed interest
  assess  — investigate: plausible link with limited evidence
  monitor — watch: industry-level relevance only
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Opportunity
from app.services.intelligence.concepts import label
from app.services.intelligence.profile import INTEREST_FIELDS, CompanyProfileModel
from app.services.intelligence.taxonomy import ADJACENCIES, ALL_CONCEPTS, DOMAIN_TECH, TECHNOLOGIES
from app.services.matching.opportunity_matching import RELEVANT_THRESHOLD, MatchResult

RING_ORDER = ("adopt", "trial", "assess", "monitor")
MATURITY_NOTE = "Not assessed: VSP has no maturity evidence for this technology in this company's context."


@dataclass
class TechRelevance:
    key: str
    score: float
    ring: str
    ring_rule: str
    relation: str
    contributions: list[dict] = field(default_factory=list)
    applications: list[dict] = field(default_factory=list)
    core_claims: list[dict] = field(default_factory=list)
    interest_claims: list[dict] = field(default_factory=list)
    related_opportunities: list[dict] = field(default_factory=list)
    uncertainties: list[str] = field(default_factory=list)
    next_step: str = ""

    def as_dict(self) -> dict:
        concept = ALL_CONCEPTS[self.key]
        return {
            "key": self.key, "name": concept.label, "area": concept.area, "description": concept.description,
            "description_source": "VSP knowledge base (general description, not company-specific evidence)",
            "score": round(self.score, 1), "ring": self.ring, "ring_rule": self.ring_rule, "relation": self.relation,
            "contributions": self.contributions, "applications": self.applications, "core_claims": self.core_claims,
            "interest_claims": self.interest_claims, "related_opportunities": self.related_opportunities,
            "uncertainties": self.uncertainties, "next_step": self.next_step, "maturity": MATURITY_NOTE,
        }


def _claim_ref(c) -> dict:  # noqa: ANN001
    return {"id": c.id, "label": c.label, "field": c.field, "claim_type": c.claim_type, "status": c.status, "evidence_id": c.evidence_id}


def assess_technologies(
    profile: CompanyProfileModel, opportunity_matches: list[tuple[Opportunity, MatchResult]]
) -> list[TechRelevance]:
    results: list[TechRelevance] = []
    new_tech_weight = profile.priorities.get("new_technology", 1)
    domain_keys = [k for k, s in profile.concepts.items() if ALL_CONCEPTS[k].kind == "domain"]

    for tech in TECHNOLOGIES:
        key = tech.key
        contributions: list[dict] = []
        support = profile.support(key)
        core_claims = [c for c in (support.claims if support else []) if c.field not in INTEREST_FIELDS and c.claim_type != "inferred"]
        interest_claims = [c for c in (support.claims if support else []) if c.field in INTEREST_FIELDS or c.claim_type == "inferred"]
        score = 0.0

        is_core = bool(core_claims) and support is not None and support.strength >= 0.69
        if is_core:
            v = 40 * support.strength
            score += v
            contributions.append({"criterion": "Documented capability", "value": round(v, 1),
                                  "explanation": f"The profile documents {label(key)} directly ({core_claims[0].label})."})

        adj_hits = []
        for adj in ADJACENCIES:
            if adj.technology != key:
                continue
            s = profile.strength(adj.capability)
            if s > 0:
                adj_hits.append((adj, s))
        if adj_hits:
            v = min(30.0, sum(15 * s for _a, s in adj_hits)) * (0.7 + 0.15 * new_tech_weight)
            v = min(30.0, v)
            score += v
            contributions.append({"criterion": "Capability adjacency", "value": round(v, 1),
                                  "explanation": "Builds on " + ", ".join(label(a.capability) for a, _ in adj_hits[:3]) + "."})

        if interest_claims:
            s = max((1.0 if c.claim_type != "inferred" else (0.9 if c.status == "confirmed" else 0.5)) for c in interest_claims)
            v = 15 * s
            score += v
            kinds = {c.claim_type for c in interest_claims}
            contributions.append({"criterion": "Stated or inferred interest", "value": round(v, 1),
                                  "explanation": ("Inferred interest (rule-based, unconfirmed)" if kinds == {"inferred"} and all(c.status != "confirmed" for c in interest_claims)
                                                  else "Interest recorded in the profile") + f": {interest_claims[0].label}."})

        industry_hits = [d for d in domain_keys if key in DOMAIN_TECH.get(d, ())]
        if industry_hits:
            v = 10.0
            score += v
            contributions.append({"criterion": "Industry relevance", "value": v,
                                  "explanation": "Commonly relevant in " + ", ".join(label(d) for d in industry_hits[:2]) + "."})

        related = [
            (opp, m) for opp, m in opportunity_matches
            if key in (opp.concepts or {}) and (opp.concepts[key].get("direct")) and m.score >= RELEVANT_THRESHOLD and m.is_actionable
        ]
        related.sort(key=lambda om: -om[1].score)
        if related:
            v = min(20.0, 7.0 * len(related))
            score += v
            contributions.append({"criterion": "Opportunity momentum", "value": round(v, 1),
                                  "explanation": f"{len(related)} open, relevant opportunit{'y' if len(related) == 1 else 'ies'} mention {label(key)}."})

        score = min(100.0, score)
        if score <= 0:
            continue

        has_link = is_core or bool(adj_hits) or any(c.claim_type != "inferred" or c.status == "confirmed" for c in interest_claims)
        if has_link and related and score >= 55:
            ring, rule = "adopt", "Documented capability link + open relevant opportunities + score ≥ 55."
        elif (is_core or adj_hits or interest_claims) and score >= 35:
            ring, rule = "trial", "Capability link or recorded interest + score ≥ 35."
        elif score >= 20 and (adj_hits or interest_claims or related):
            ring, rule = "assess", "Plausible link with limited evidence (score ≥ 20)."
        else:
            ring, rule = "monitor", "Industry-level relevance only, or weak signal."

        relation = "core" if is_core else ("adjacent" if adj_hits else ("interest" if interest_claims else "industry"))
        uncertainties = [MATURITY_NOTE]
        if relation in ("adjacent", "interest", "industry"):
            uncertainties.append("The company has not stated that it uses this technology; the link is a rule-based hypothesis.")
        if interest_claims and all(c.claim_type == "inferred" and c.status != "confirmed" for c in interest_claims):
            uncertainties.append("The interest is inferred and not yet confirmed by the company.")
        if not related:
            uncertainties.append("No open, relevant opportunity in the collected data mentions this technology.")

        applications = [
            {"capability": label(a.capability), "capability_claims": profile.claim_labels(a.capability, 2), "rationale": a.rationale,
             "application": a.application, "benefit": a.benefit, "basis": "VSP knowledge base hypothesis"}
            for a, _s in adj_hits[:3]
        ]
        if is_core:
            next_step = f"{label(key)} is already part of the documented technology base; use the related opportunities to fund its next development step."
        elif applications:
            next_step = f"Scope a small pilot: {applications[0]['application']}"
        elif related:
            next_step = f"Review '{related[0][0].title}' to learn how {label(key)} is being funded in your sector."
        else:
            next_step = f"Keep {label(key)} on the watch list; revisit when new opportunities or partner capabilities appear."

        results.append(TechRelevance(
            key=key, score=score, ring=ring, ring_rule=rule, relation=relation, contributions=contributions,
            applications=applications, core_claims=[_claim_ref(c) for c in core_claims[:3]],
            interest_claims=[_claim_ref(c) for c in interest_claims[:3]],
            related_opportunities=[{"id": o.id, "title": o.title, "relevance_score": m.score, "category": o.category,
                                    "deadline_at": o.deadline_at.isoformat() if o.deadline_at else None} for o, m in related[:4]],
            uncertainties=uncertainties, next_step=next_step,
        ))
    results.sort(key=lambda r: (RING_ORDER.index(r.ring), -r.score))
    return results
