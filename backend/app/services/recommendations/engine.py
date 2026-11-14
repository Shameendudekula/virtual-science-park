"""Recommendation engine: combines opportunities, technologies and collaborations into ranked actions.

Ranking is a transparent sum of five criteria (max 100). Tiers come from explicit rules:
  high    — rank ≥ 55, evidence strength ≥ 6 and not resting on unconfirmed inferences only
  medium  — rank ≥ 42
  later   — everything else that passed the candidate thresholds
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from app.models import Opportunity
from app.services.intelligence.concepts import label
from app.services.intelligence.profile import CompanyProfileModel
from app.services.intelligence.taxonomy import PRIORITIES
from app.services.matching.complementarity import CollaborationResult, collaboration_detail
from app.services.matching.opportunity_matching import RELEVANT_THRESHOLD, MatchResult
from app.services.matching.technology_relevance import TechRelevance

KIND_LABELS = {
    "apply_funding": "Apply for funding",
    "research_proposal": "Develop a research proposal",
    "attend_event": "Participate in an event",
    "investigate_facility": "Investigate a test environment",
    "join_programme": "Explore a programme",
    "contact_partner": "Contact a potential partner",
    "explore_technology": "Explore a technology",
    "form_consortium": "Form a consortium",
}

# Which company priority each recommendation kind serves (primary first).
KIND_PRIORITY: dict[str, tuple[tuple[str, float], ...]] = {
    "apply_funding": (("find_funding", 1.0), ("improve_products", 0.5)),
    "research_proposal": (("research_collaboration", 1.0), ("find_funding", 0.6)),
    "attend_event": (("new_industries", 0.7), ("new_technology", 0.6)),
    "investigate_facility": (("testing_facilities", 1.0), ("improve_products", 0.5)),
    "join_programme": (("new_industries", 0.8), ("find_funding", 0.4)),
    "explore_technology": (("new_technology", 1.0), ("improve_products", 0.6)),
    "form_consortium": (("find_funding", 0.8), ("research_collaboration", 0.8)),
}
CATEGORY_KIND = {
    "funding_call": "apply_funding", "innovation_programme": "apply_funding", "research_funding": "research_proposal",
    "research_collaboration": "research_proposal", "event": "attend_event", "testing_facility": "investigate_facility",
    "business_programme": "join_programme",
}
RELATION_PRIORITY = {"research": "research_collaboration", "testing_validation": "testing_facilities", "component_supply": "improve_products",
                     "digital_infrastructure": "new_technology", "security": "new_industries", "market_access": "new_industries"}


@dataclass
class Candidate:
    fingerprint: str
    kind: str
    title: str
    summary: str
    base: float  # 0..1 normalised stage relevance
    evidence_strength: float  # 0..10
    inferred_only: bool
    urgency: float  # 0..15
    actionability: float  # 0..10
    detail: dict
    priority_keys: tuple[tuple[str, float], ...]
    related_opportunity_id: int | None = None
    related_company_id: int | None = None
    related_technology_key: str | None = None
    rank: float = 0.0
    tier: str = "later"
    criteria: list[dict] = field(default_factory=list)


def _urgency(m: MatchResult) -> float:
    t = m.timeliness
    days = t.get("days_left")
    if t["status"] == "closing_soon":
        return 15.0
    if t["status"] in ("open", "upcoming") and days is not None:
        return 12.0 if days <= 60 else (9.0 if days <= 120 else 6.0)
    return 4.0


def _evidence_strength_opp(m: MatchResult) -> float:
    return {"high": 10.0, "medium": 7.0, "limited": 3.0}[m.evidence_quality["level"]]


def _claims_inferred_only(m: MatchResult, profile: CompanyProfileModel) -> bool:
    ids = set(m.supporting_claim_ids)
    claims = [c for c in profile.claims if c.id in ids]
    return bool(claims) and all(c.claim_type == "inferred" and c.status != "confirmed" for c in claims)


def opportunity_candidates(profile: CompanyProfileModel, matches: list[tuple[Opportunity, MatchResult]]) -> list[Candidate]:
    out = []
    for opp, m in matches:
        kind = CATEGORY_KIND.get(opp.category)
        if not kind or not m.is_actionable or m.score < RELEVANT_THRESHOLD:
            continue
        verb = {"apply_funding": "Prepare an application", "research_proposal": "Develop a research proposal", "attend_event": "Consider participating",
                "investigate_facility": "Investigate the test environment", "join_programme": "Explore the programme"}[kind]
        caps = [r for c in m.criteria for r in c.matches][:3]
        out.append(Candidate(
            fingerprint=f"opp:{opp.id}", kind=kind, title=f"{verb}: {opp.title}",
            summary=m.business_value, base=m.score / 100, evidence_strength=_evidence_strength_opp(m),
            inferred_only=_claims_inferred_only(m, profile), urgency=_urgency(m),
            actionability=10.0 if (opp.apply_url or opp.source_url) else 6.0,
            priority_keys=KIND_PRIORITY[kind], related_opportunity_id=opp.id,
            detail={
                "what": f"{verb}: {opp.title} ({opp.organisation}).",
                "why": m.reasons,
                "capabilities": [{"concept": r["label"], "claims": r["company_claims"]} for r in caps],
                "business_value": m.business_value,
                "evidence_ids": [opp.evidence_id] if opp.evidence_id else [],
                "claim_ids": m.supporting_claim_ids,
                "uncertainties": m.missing_information + [m.eligibility["note"]],
                "next_step": m.next_action,
                "match": {"relevance_score": m.score, "relevance_band": m.band,
                          "criteria": [c.as_dict() for c in m.criteria], "penalties": m.penalties},
                "opportunity": {"id": opp.id, "title": opp.title, "category": opp.category, "organisation": opp.organisation,
                                "deadline_at": opp.deadline_at.isoformat() if opp.deadline_at else None,
                                "source_url": opp.source_url, "apply_url": opp.apply_url, "provenance": opp.provenance},
            },
        ))
    return out


def technology_candidates(profile: CompanyProfileModel, techs: list[TechRelevance]) -> list[Candidate]:
    out = []
    for t in techs:
        if t.ring not in ("adopt", "trial") or t.relation == "core":
            continue
        app = t.applications[0] if t.applications else None
        cap_text = f" for {app['capability'].lower()}" if app else ""
        inferred_only = t.relation == "interest" and all(c["claim_type"] == "inferred" and c["status"] != "confirmed" for c in t.interest_claims)
        evidence_ids = sorted({c["evidence_id"] for c in t.core_claims if c.get("evidence_id")})
        claim_ids = [c["id"] for c in (*t.core_claims, *t.interest_claims) if c.get("id")]
        cap_claims: list[dict] = []
        if app:
            for k, s in profile.concepts.items():
                if label(k) == app["capability"]:
                    cap_claims = [{"id": c.id, "label": c.label, "claim_type": c.claim_type, "status": c.status} for c in s.claims[:2]]
                    claim_ids += [c.id for c in s.claims[:2] if c.id]
                    evidence_ids += [c.evidence_id for c in s.claims[:2] if c.evidence_id]
        out.append(Candidate(
            fingerprint=f"tech:{t.key}", kind="explore_technology", title=f"Explore {label(t.key)}{cap_text}",
            summary=app["benefit"] if app else t.next_step, base=t.score / 100, evidence_strength=4.0 if inferred_only else 6.0,
            inferred_only=inferred_only, urgency=5.0, actionability=7.0, priority_keys=KIND_PRIORITY["explore_technology"],
            related_technology_key=t.key,
            detail={
                "what": f"Explore {label(t.key)}{cap_text} (radar ring: {t.ring}).",
                "why": [c["explanation"] for c in t.contributions],
                "capabilities": [{"concept": app["capability"], "claims": cap_claims}] if app else [],
                "business_value": app["benefit"] if app else "Strengthening an existing technology base.",
                "evidence_ids": sorted(set(evidence_ids)), "claim_ids": sorted(set(claim_ids)),
                "uncertainties": t.uncertainties, "next_step": t.next_step,
                "technology": {"key": t.key, "name": label(t.key), "ring": t.ring, "score": round(t.score, 1), "ring_rule": t.ring_rule},
                "applications": t.applications,
            },
        ))
    return out


def partner_candidates(profile: CompanyProfileModel, collabs: list[CollaborationResult]) -> list[Candidate]:
    out = []
    for r in collabs:
        if r.score < 25:
            continue
        d = collaboration_detail(profile, r)
        top = r.fired[0]
        prio = RELATION_PRIORITY.get(top.rule.relation, "new_industries")
        inferred_only = False
        out.append(Candidate(
            fingerprint=f"partner:{r.partner.company.id}", kind="contact_partner",
            title=f"Explore a potential collaboration with {r.partner.company.name}",
            summary=d["scenario"], base=r.score / 100,
            evidence_strength=8.0 if r.partner.company.profile_level == "full" else 6.5, inferred_only=inferred_only,
            urgency=5.0, actionability=8.0, priority_keys=((prio, 1.0), ("research_collaboration", 0.3)),
            related_company_id=r.partner.company.id,
            detail={
                "what": f"Potential collaboration with {r.partner.company.name} ({r.strength} complementarity). Not an existing partnership.",
                "why": d["why"],
                "capabilities": [{"concept": f["need"]["label"] if f["seeker_id"] == profile.company.id else f["offer"]["label"],
                                  "claims": f["need"]["claims"] if f["seeker_id"] == profile.company.id else f["offer"]["claims"]} for f in d["rules"][:2]],
                "business_value": d["mutual_benefit"]["for_company"],
                "evidence_ids": [], "claim_ids": d["evidence_claim_ids"], "uncertainties": d["uncertainties"] + d["missing_information"],
                "next_step": d["first_step"], "collaboration": d,
            },
        ))
    return out


def consortium_candidates(
    profile: CompanyProfileModel, matches: dict[int, MatchResult], opps: dict[int, Opportunity], collabs: list[CollaborationResult],
) -> list[Candidate]:
    out = []
    for r in collabs:
        if r.score < 30:
            continue
        for so in r.shared_opportunities:
            m = matches.get(so["id"])
            if not m or not so["requires_consortium"] or m.score < 40:
                continue
            opp = opps[so["id"]]
            out.append(Candidate(
                fingerprint=f"consortium:{opp.id}:{r.partner.company.id}", kind="form_consortium",
                title=f"Explore a joint application with {r.partner.company.name}: {opp.title}",
                summary=f"The call text mentions multiple participants, and both organisations match it ({m.score} and {so['partner_score']}).",
                base=(m.score + so["partner_score"] + r.score) / 300, evidence_strength=_evidence_strength_opp(m), inferred_only=False,
                urgency=_urgency(m), actionability=9.0, priority_keys=KIND_PRIORITY["form_consortium"],
                related_opportunity_id=opp.id, related_company_id=r.partner.company.id,
                detail={
                    "what": f"Consider approaching {r.partner.company.name} about a joint application to '{opp.title}'.",
                    "why": [
                        f"The source's 'who can apply' text mentions multiple participants: “{(opp.eligibility_text or '')[:220]}”",
                        f"{profile.company.name}'s relevance to the call: {m.score}/100; {r.partner.company.name}'s: {so['partner_score']}/100.",
                        *collaboration_detail(profile, r)["why"][:1],
                    ],
                    "capabilities": [],
                    "business_value": m.business_value,
                    "evidence_ids": [opp.evidence_id] if opp.evidence_id else [],
                    "claim_ids": m.supporting_claim_ids,
                    "uncertainties": ["Neither organisation has expressed interest in a joint application; this is a VSP suggestion.",
                                      m.eligibility["note"], *m.missing_information[:2]],
                    "next_step": f"Validate the project idea internally, then contact {r.partner.company.name} with a one-page outline well before the deadline.",
                    "opportunity": {"id": opp.id, "title": opp.title, "category": opp.category, "organisation": opp.organisation,
                                    "deadline_at": opp.deadline_at.isoformat() if opp.deadline_at else None,
                                    "source_url": opp.source_url, "apply_url": opp.apply_url, "provenance": opp.provenance},
                    "partner": {"id": r.partner.company.id, "name": r.partner.company.name},
                },
            ))
    out.sort(key=lambda c: -c.base)
    return out[:2]


def rank(profile: CompanyProfileModel, candidates: list[Candidate]) -> list[Candidate]:
    for c in candidates:
        relevance = 40 * c.base
        prio_val, prio_key = 0.0, None
        for key, affinity in c.priority_keys:
            v = (profile.priorities.get(key, 1) / 3) * affinity
            if v > prio_val:
                prio_val, prio_key = v, key
        priority = 25 * prio_val
        primary_key = c.priority_keys[0][0]
        deprioritised = profile.priorities.get(primary_key, 1) == 0
        penalty = -12.0 if deprioritised else 0.0
        c.rank = max(0.0, relevance + priority + c.urgency + c.evidence_strength + c.actionability + penalty)
        c.criteria = [
            {"criterion": "Stage relevance", "value": round(relevance, 1), "max": 40, "explanation": "Relevance from the matching stage that produced this recommendation."},
            {"criterion": "Priority alignment", "value": round(priority, 1), "max": 25,
             "explanation": (f"Serves '{PRIORITIES[prio_key]['label']}' (weight {profile.priorities.get(prio_key, 1)}/3)." if prio_key else "No priority alignment.")},
            {"criterion": "Urgency", "value": round(c.urgency, 1), "max": 15, "explanation": "Based on the stated deadline, if any."},
            {"criterion": "Evidence strength", "value": round(c.evidence_strength, 1), "max": 10, "explanation": "Quality of the records and claims behind it."},
            {"criterion": "Actionability", "value": round(c.actionability, 1), "max": 10, "explanation": "Whether a concrete next step and source link exist."},
        ]
        if deprioritised:
            c.criteria.append({"criterion": "De-prioritised", "value": penalty, "max": 0,
                               "explanation": f"'{PRIORITIES[primary_key]['label']}' is set to 'not a priority'."})
        if c.rank >= 55 and c.evidence_strength >= 6 and not c.inferred_only:
            c.tier = "high"
        elif c.rank >= 42:
            c.tier = "medium"
        else:
            c.tier = "later"
        c.detail["tier_rule"] = {
            "high": "Rank ≥ 55, evidence strength ≥ 6, and not based only on unconfirmed inferences.",
            "medium": "Rank ≥ 42.",
            "later": "Passed candidate thresholds but rank < 42.",
        }[c.tier]
    candidates.sort(key=lambda c: (-c.rank, c.fingerprint))
    return candidates


def executive_summary(profile: CompanyProfileModel, ranked: list[Candidate], techs: list[TechRelevance],
                      collabs: list[CollaborationResult], relevant_count: int, today: date) -> dict:
    name = profile.company.name
    overview = next((c.value for c in profile.effective_claims if c.field == "overview"), None)
    top = [c for c in ranked if c.tier == "high"][:3] or ranked[:3]
    trial = [t for t in techs if t.ring in ("adopt", "trial") and t.relation != "core"][:2]
    partner = collabs[0] if collabs else None
    deadlines = sorted(
        [c for c in ranked if c.detail.get("opportunity", {}).get("deadline_at") and c.kind in ("apply_funding", "research_proposal", "form_consortium")],
        key=lambda c: c.detail["opportunity"]["deadline_at"],
    )
    bullets = []
    if overview:
        bullets.append(f"{name}: {overview}")
    bullets.append(f"{relevant_count} open opportunities in the collected data are relevant (score ≥ {RELEVANT_THRESHOLD}).")
    if top:
        bullets.append("Top action: " + top[0].title + ".")
    if deadlines:
        d = deadlines[0].detail["opportunity"]
        bullets.append(f"Nearest relevant deadline: {d['deadline_at'][:10]} — {d['title']}.")
    if trial:
        bullets.append("Technologies to trial: " + ", ".join(label(t.key) for t in trial) + ".")
    if partner:
        bullets.append(f"Strongest potential partner: {partner.partner.company.name} (potential, not an existing partnership).")
    return {
        "headline": f"{len([c for c in ranked if c.tier == 'high'])} high-priority actions for {name}",
        "bullets": bullets,
        "generated_by": "deterministic template over application records",
        "as_of": today.isoformat(),
    }
