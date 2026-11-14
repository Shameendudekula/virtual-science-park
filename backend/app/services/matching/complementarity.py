"""Company-to-company complementarity. Similarity alone never produces a suggestion.

A suggestion requires at least one complementarity rule to fire (a documented need on one side and a
documented offer on the other). Shared industries and shared open opportunities only add context.
Suggestions are always *potential* collaborations; existing partnerships are never implied.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from app.models import Opportunity
from app.services.intelligence.concepts import label
from app.services.intelligence.geography import proximity
from app.services.intelligence.profile import INTEREST_FIELDS, CompanyProfileModel
from app.services.intelligence.taxonomy import ALL_CONCEPTS, COMPLEMENTARITY_RULES, ComplementarityRule
from app.services.matching.opportunity_matching import MatchResult

DISCLAIMER = (
    "Potential collaboration suggested by VSP's rules from public information. It does not mean that either organisation "
    "has agreed to, discussed or is interested in collaborating."
)


@dataclass
class FiredRule:
    rule: ComplementarityRule
    seeker: CompanyProfileModel
    provider: CompanyProfileModel
    need_key: str
    offer_key: str
    contribution: float

    def as_dict(self) -> dict:
        r = self.rule
        fmt = {
            "seeker": self.seeker.company.name, "provider": self.provider.company.name,
            "need_label": label(self.need_key).lower(), "offer_label": label(self.offer_key).lower(),
        }
        return {
            "rule": r.key, "relation": r.relation, "strength": r.strength, "contribution": round(self.contribution, 1),
            "direction": f"{self.seeker.company.name} → {self.provider.company.name}",
            "seeker_id": self.seeker.company.id, "provider_id": self.provider.company.id,
            "need": {"concept": self.need_key, "label": label(self.need_key), "claims": _refs(self.seeker, self.need_key)},
            "offer": {"concept": self.offer_key, "label": label(self.offer_key), "claims": _refs(self.provider, self.offer_key)},
            "rationale": r.rationale.format(**fmt), "scenario": r.scenario.format(**fmt),
            "seeker_benefit": r.seeker_benefit, "provider_benefit": r.provider_benefit, "first_step": r.first_step.format(**fmt),
            "priority_key": r.priority_key, "basis": "VSP complementarity rule (hypothesis based on documented capabilities)",
        }


def _refs(profile: CompanyProfileModel, key: str) -> list[dict]:
    s = profile.support(key)
    if not s:
        return []
    return [{"id": c.id, "label": c.label, "claim_type": c.claim_type, "status": c.status, "evidence_id": c.evidence_id} for c in s.claims[:2]]


def _capability_strength(profile: CompanyProfileModel, key: str) -> float:
    """Needs and offers must come from capability-type evidence, not from interests alone."""
    s = profile.support(key)
    if not s:
        return 0.0
    if s.via_interest_only:
        return 0.0
    return s.strength


@dataclass
class CollaborationResult:
    partner: CompanyProfileModel
    score: float
    strength: str
    fired: list[FiredRule]
    shared_context: list[str]
    shared_opportunities: list[dict]
    uncertainties: list[str]
    criteria: list[dict] = field(default_factory=list)
    proximity: dict = field(default_factory=dict)


def _fire(seeker: CompanyProfileModel, provider: CompanyProfileModel) -> list[FiredRule]:
    fired = []
    for rule in COMPLEMENTARITY_RULES:
        needs = sorted(((k, _capability_strength(seeker, k)) for k in rule.need), key=lambda t: -t[1])
        offers = sorted(((k, _capability_strength(provider, k)) for k in rule.offer), key=lambda t: -t[1])
        if needs and offers and needs[0][1] > 0 and offers[0][1] > 0:
            weight = seeker.priorities.get(rule.priority_key, 1) if rule.priority_key else 1
            contribution = 30 * rule.strength * min(needs[0][1], offers[0][1]) * (0.7 + 0.15 * weight)
            fired.append(FiredRule(rule, seeker, provider, needs[0][0], offers[0][0], contribution))
    return fired


def assess_pair(
    company: CompanyProfileModel,
    partner: CompanyProfileModel,
    company_matches: dict[int, MatchResult] | None = None,
    partner_matches: dict[int, MatchResult] | None = None,
    opportunities: dict[int, Opportunity] | None = None,
) -> CollaborationResult | None:
    if company.company.id == partner.company.id:
        return None
    fired = _fire(company, partner) + _fire(partner, company)
    if not fired:
        return None  # similarity alone is never enough
    fired.sort(key=lambda f: -f.contribution)
    rule_value = min(78.0, sum(f.contribution for f in fired))
    criteria = [{"criterion": "Complementary capabilities", "value": round(rule_value, 1), "max": 78,
                 "explanation": f"{len(fired)} complementarity rule(s) fired."}]

    shared = [k for k, s in company.concepts.items()
              if ALL_CONCEPTS[k].kind in ("domain", "technology") and partner.has(k) and ALL_CONCEPTS[k].specificity >= 0.6]
    context_value = min(10.0, 2.5 * len(shared))
    criteria.append({"criterion": "Shared context", "value": round(context_value, 1), "max": 10,
                     "explanation": ("Shared areas: " + ", ".join(label(k) for k in shared[:4])) if shared else "No shared industry or technology area."})

    shared_opps: list[dict] = []
    if company_matches and partner_matches and opportunities:
        for opp_id, m in company_matches.items():
            pm = partner_matches.get(opp_id)
            if pm and m.is_actionable and m.score >= 35 and pm.score >= 30:
                opp = opportunities[opp_id]
                shared_opps.append({"id": opp_id, "title": opp.title, "company_score": m.score, "partner_score": pm.score,
                                    "requires_consortium": m.requires_consortium, "category": opp.category})
        shared_opps.sort(key=lambda o: -(o["company_score"] + o["partner_score"] + (20 if o["requires_consortium"] else 0)))
    opp_value = min(12.0, sum(5 + (3 if o["requires_consortium"] else 0) for o in shared_opps[:2]))
    criteria.append({"criterion": "Joint opportunity potential", "value": round(opp_value, 1), "max": 12,
                     "explanation": (f"{len(shared_opps)} open opportunit{'y is' if len(shared_opps) == 1 else 'ies are'} relevant to both" +
                                     (" (some mention multi-party consortia)." if any(o['requires_consortium'] for o in shared_opps) else ".")) if shared_opps
                     else "No open opportunity is relevant to both organisations."})

    prox_value, prox_why = (proximity(company.geo, partner.geo, rule_value, company.priorities.get("regional_focus", 1))
                            if company.geo and partner.geo else (0.0, "Location unknown."))
    criteria.append({"criterion": "Regional proximity", "value": round(prox_value, 1), "max": 10, "explanation": prox_why})

    score = min(100.0, rule_value + context_value + opp_value + prox_value)
    strength = "strong" if score >= 45 and fired[0].rule.strength >= 0.8 else ("moderate" if score >= 25 else "exploratory")

    uncertainties = [DISCLAIMER]
    if partner.company.profile_level != "full":
        uncertainties.append(f"{partner.company.name}'s profile is partial (built from a single official page); capabilities may be incomplete.")
    if any(c.claim_type == "inferred" for f in fired for k in (f.need_key,) for c in (f.seeker.support(k).claims if f.seeker.support(k) else [])):
        uncertainties.append("Part of the need side rests on inferred information.")
    if all(f.rule.strength < 0.6 for f in fired):
        uncertainties.append("Only exploratory rules fired; treat as a hypothesis to test, not a recommendation to commit.")
    uncertainties.append("Commercial interest, capacity, and existing contracts of either party are unknown to VSP.")

    return CollaborationResult(partner=partner, score=score, strength=strength, fired=fired, shared_context=shared[:6],
                               shared_opportunities=shared_opps[:4], uncertainties=uncertainties, criteria=criteria,
                               proximity={"value": round(prox_value, 1), "explanation": prox_why,
                                          "partner_location": partner.geo.as_dict() if partner.geo else None})


def collaboration_detail(company: CompanyProfileModel, result: CollaborationResult) -> dict:
    top = result.fired[0]
    p = result.partner.company
    capabilities = [c.label for c in result.partner.effective_claims if c.field in ("capability", "product", "service", "technology")][:6]
    technologies = sorted({label(k) for k, s in result.partner.concepts.items() if ALL_CONCEPTS[k].kind == "technology" and not s.via_interest_only})[:6]
    complementary = []
    for f in result.fired:
        d = f.as_dict()
        complementary.append(d)
    gives = sorted({f.offer_key for f in result.fired if f.provider.company.id == p.id})
    gets = sorted({f.offer_key for f in result.fired if f.provider.company.id == company.company.id})
    missing = []
    if not any(c.field == "documented_collaboration" for c in result.partner.effective_claims):
        missing.append(f"No publicly documented collaborations of {p.name} were collected.")
    if p.profile_level != "full":
        missing.append(f"{p.name} has a partial profile; products and priorities beyond the collected page are unknown.")
    overview = next((c.value for c in result.partner.effective_claims if c.field == "overview"), None)
    return {
        "partner": {"id": p.id, "name": p.name, "slug": p.slug, "website": p.website, "profile_level": p.profile_level,
                    "organisation_type": p.organisation_type, "membership_status": p.membership_status, "description": overview},
        "score": round(result.score, 1), "strength": result.strength, "status": "potential",
        "location": result.proximity.get("partner_location"), "proximity": result.proximity,
        "criteria": result.criteria,
        "core_capabilities": capabilities, "relevant_technologies": technologies,
        "complementary_capabilities": {"partner_offers": [label(k) for k in gives], "company_offers": [label(k) for k in gets]},
        "why": [f.as_dict()["rationale"] for f in result.fired[:3]],
        "scenario": top.as_dict()["scenario"],
        "mutual_benefit": {"for_company": top.rule.seeker_benefit if top.seeker.company.id == company.company.id else top.rule.provider_benefit,
                           "for_partner": top.rule.provider_benefit if top.seeker.company.id == company.company.id else top.rule.seeker_benefit},
        "rules": complementary, "shared_context": [label(k) for k in result.shared_context],
        "shared_opportunities": result.shared_opportunities,
        "evidence_claim_ids": sorted({c["id"] for f in complementary for side in ("need", "offer") for c in f[side]["claims"] if c["id"]}),
        "missing_information": missing, "uncertainties": result.uncertainties,
        "first_step": top.as_dict()["first_step"], "disclaimer": DISCLAIMER,
    }


def interest_only(profile: CompanyProfileModel, key: str) -> bool:
    s = profile.support(key)
    return bool(s and all(c.field in INTEREST_FIELDS for c in s.claims))
