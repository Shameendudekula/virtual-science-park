"""Opportunity matching: transparent, criterion-based relevance of an opportunity to a company.

Four separate dimensions are reported and never merged:
  * relevance score  — heuristic 0-100 from explicit criteria (NOT a probability)
  * evidence quality — how good the underlying record is
  * completeness     — which decision-relevant fields the source provides
  * eligibility      — always 'not assessed by VSP'; source text shown verbatim when available
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from app.models import Opportunity
from app.services.intelligence.concepts import label
from app.services.intelligence.geography import GEO_LABELS, regional_relevance
from app.services.intelligence.profile import CompanyProfileModel
from app.services.intelligence.taxonomy import ALL_CONCEPTS, PRIORITIES, PRIORITY_CATEGORY_AFFINITY

MAX = {"technology_fit": 35, "industry_fit": 20, "capability_fit": 15, "priority_alignment": 15, "timeliness": 10, "evidence_availability": 5,
       "regional_relevance": 10}
CRITERION_LABELS = {
    "technology_fit": "Technology fit",
    "industry_fit": "Industry fit",
    "capability_fit": "Capability & need fit",
    "priority_alignment": "Priority alignment",
    "timeliness": "Timeliness",
    "evidence_availability": "Evidence availability",
    "regional_relevance": "Regional relevance",
}
CONSORTIUM_RE = re.compile(r"at least two|minst två|consorti|konsorti|two participants|projektparter|several parties|flera parter", re.I)
RELEVANT_THRESHOLD = 35
EVENT_RECENCY_DAYS = 120

NEED_MARKERS = frozenset({"prototype_validation", "certified_products"})

# Opportunity categories where a company *need* (rather than a shared topic) creates fit.
NEED_RULES: dict[str, tuple[tuple[str, ...], str]] = {
    "testing_facility": (("prototype_validation", "certified_products"), "The company documents prototype validation or certified products, which require test environments."),
    "research_collaboration": (("simulation_modelling", "control_algorithms", "ai_platform", "academic_research"), "The company documents R&D-intensive capabilities suitable for collaborative research."),
    "research_funding": (("simulation_modelling", "control_algorithms", "ai_platform", "academic_research", "prototype_validation"), "The company documents R&D-intensive capabilities suitable for research projects."),
}


@dataclass
class Criterion:
    key: str
    value: float
    max: int
    explanation: str
    matches: list[dict] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"key": self.key, "label": CRITERION_LABELS[self.key], "value": round(self.value, 1), "max": self.max,
                "explanation": self.explanation, "matches": self.matches}


@dataclass
class MatchResult:
    opportunity_id: int
    score: int
    band: str
    criteria: list[Criterion]
    penalties: list[dict]
    reasons: list[str]
    missing_information: list[str]
    timeliness: dict
    evidence_quality: dict
    completeness: dict
    eligibility: dict
    business_value: str
    next_action: str
    requires_consortium: bool
    supporting_claim_ids: list[int]
    is_actionable: bool
    geography: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {
            "opportunity_id": self.opportunity_id, "relevance_score": self.score, "relevance_band": self.band,
            "criteria": [c.as_dict() for c in self.criteria], "penalties": self.penalties, "reasons": self.reasons,
            "missing_information": self.missing_information, "timeliness": self.timeliness,
            "evidence_quality": self.evidence_quality, "completeness": self.completeness, "eligibility": self.eligibility,
            "business_value": self.business_value, "next_action": self.next_action,
            "requires_consortium": self.requires_consortium, "supporting_claim_ids": self.supporting_claim_ids,
            "is_actionable": self.is_actionable, "geography": self.geography,
            "score_note": "Heuristic relevance score from the listed criteria. It is not a probability of success or of eligibility.",
        }


def band(score: int) -> str:
    if score >= 55:
        return "strong"
    if score >= RELEVANT_THRESHOLD:
        return "moderate"
    if score >= 20:
        return "weak"
    return "low"


def timeliness(opp: Opportunity, today: date) -> dict:
    if opp.category == "event" or opp.category in ("ecosystem_news", "business_programme", "testing_facility") and opp.deadline_at is None:
        published = opp.published_at.date() if opp.published_at else None
        age = (today - published).days if published else None
        if opp.category == "event":
            recent = age is not None and age <= EVENT_RECENCY_DAYS
            return {"status": "date_unknown", "days_left": None, "published_days_ago": age, "recent": recent,
                    "label": "Event date not in collected metadata" + ("" if recent else " — published over 4 months ago, may have passed")}
        return {"status": "no_deadline", "days_left": None, "published_days_ago": age, "recent": age is not None and age <= 365,
                "label": "No deadline (information item)"}
    if opp.deadline_status == "placeholder_rejected":
        return {"status": "placeholder_rejected", "days_left": None, "label": "Deadline not stated (placeholder date in source rejected)"}
    if opp.deadline_at is None:
        return {"status": "no_deadline", "days_left": None, "label": "Deadline not stated in source"}
    days = (opp.deadline_at.date() - today).days
    if days < 0:
        return {"status": "closed", "days_left": days, "label": "Closed"}
    if opp.opens_at and opp.opens_at.date() > today:
        return {"status": "upcoming", "days_left": days, "opens_in": (opp.opens_at.date() - today).days,
                "label": f"Opens {opp.opens_at.date().isoformat()}"}
    if days <= 21:
        return {"status": "closing_soon", "days_left": days, "label": f"Closes in {days} days"}
    return {"status": "open", "days_left": days, "label": f"Open — {days} days left"}


def evidence_quality(opp: Opportunity) -> dict:
    if "metadata_only" in (opp.quality_flags or []):
        return {"level": "limited", "label": "Limited — title-level metadata only",
                "explanation": "Only title, date and link were collected (content reuse not confirmed). Open the source to verify details."}
    if opp.purpose_text and opp.description:
        return {"level": "high", "label": "High — official funder record",
                "explanation": f"Structured record from the {opp.organisation} public API with description and call text."}
    return {"level": "medium", "label": "Medium — official record, partial text",
            "explanation": f"Official {opp.organisation} record, but some descriptive fields are empty."}


def completeness(opp: Opportunity) -> dict:
    checks = {
        "description": bool(opp.description or opp.purpose_text),
        "deadline": opp.deadline_status == "stated",
        "eligibility_text": bool(opp.eligibility_text),
        "funding_amount": bool(opp.funding_text),
        "application_link": bool(opp.apply_url),
    }
    if opp.category in ("event", "ecosystem_news", "business_programme", "testing_facility"):
        checks = {"description": bool(opp.description), "date": opp.deadline_status == "stated", "source_link": bool(opp.source_url)}
    present = [k for k, v in checks.items() if v]
    missing = [k for k, v in checks.items() if not v]
    return {"score_pct": round(100 * len(present) / len(checks)), "present": present, "missing": missing}


def eligibility(opp: Opportunity) -> dict:
    if opp.eligibility_text:
        return {"status": "source_text_available", "text": opp.eligibility_text,
                "note": "Quoted from the source. VSP does not assess whether the company is eligible."}
    return {"status": "not_stated", "text": None, "note": "Not stated in source. Confirm eligibility on the official call page before applying."}


def score_opportunity(profile: CompanyProfileModel, opp: Opportunity, today: date) -> MatchResult:
    oc: dict[str, dict] = opp.concepts or {}
    criteria: dict[str, Criterion] = {}
    supporting: set[int] = set()

    def matched(kind: str) -> list[tuple[str, dict, float, float]]:
        out = []
        for key, info in oc.items():
            concept = ALL_CONCEPTS.get(key)
            if concept is None or concept.kind != kind:
                continue
            s = profile.strength(key)
            if s > 0:
                out.append((key, info, s, concept.specificity))
        return sorted(out, key=lambda t: -(t[1]["weight"] * t[2] * t[3]))

    def match_rows(rows: list[tuple[str, dict, float, float]]) -> list[dict]:
        result = []
        for key, info, s, _spec in rows:
            support = profile.support(key)
            claims = support.claims[:3] if support else []
            supporting.update(c.id for c in claims if c.id)
            result.append({
                "concept": key, "label": label(key), "opportunity_terms": info["terms"], "opportunity_field": info["field"],
                "company_claims": [{"id": c.id, "label": c.label, "claim_type": c.claim_type, "status": c.status} for c in claims],
                "company_strength": round(s, 2),
            })
        return result

    # 1. Technology fit
    tech = matched("technology")
    tech_value = min(MAX["technology_fit"], sum(20 * i["weight"] * s * spec for _k, i, s, spec in tech))
    criteria["technology_fit"] = Criterion("technology_fit", tech_value, MAX["technology_fit"],
        ("Shared technology areas: " + ", ".join(label(k) for k, *_ in tech[:4])) if tech else "No technology area of the opportunity appears in the company profile.",
        match_rows(tech[:4]))

    # 2. Industry fit
    dom = matched("domain")
    dom_value = min(MAX["industry_fit"], sum(12 * i["weight"] * s * spec for _k, i, s, spec in dom))
    criteria["industry_fit"] = Criterion("industry_fit", dom_value, MAX["industry_fit"],
        ("Shared industries: " + ", ".join(label(k) for k, *_ in dom[:3])) if dom else "No shared industry.", match_rows(dom[:3]))

    # 3. Capability & need fit
    # Need markers describe what a company *needs* (e.g. validating prototypes). A word like "validation" in an
    # opportunity is not a topical match, so these only feed the need bonus below, never topical fit.
    cap = [row for row in matched("capability") if row[0] not in NEED_MARKERS]
    cap_value = min(MAX["capability_fit"], sum(10 * i["weight"] * s * spec for _k, i, s, spec in cap))
    topical_cap = list(cap)
    cap_expl = ("Specific capability terms in the opportunity: " + ", ".join(label(k) for k, *_ in cap[:3])) if cap else ""
    need = NEED_RULES.get(opp.category)
    if need:
        hits = [k for k in need[0] if profile.has(k)]
        # A generic need (e.g. "needs testing") only counts when the opportunity is also topically related.
        if hits and (tech or cap or dom):
            cap_value = min(MAX["capability_fit"], cap_value + 8 * max(profile.strength(k) for k in hits))
            cap_expl = (cap_expl + " " if cap_expl else "") + need[1]
            cap += [(k, {"terms": ["(category need)"], "field": "category", "weight": 1.0}, profile.strength(k), 1.0) for k in hits[:2]]
    criteria["capability_fit"] = Criterion("capability_fit", cap_value, MAX["capability_fit"], cap_expl or "No specific capability or need match.", match_rows(cap[:4]))

    # 4. Priority alignment
    best = (0.0, None)
    for pkey, weight in profile.priorities.items():
        affinity = PRIORITY_CATEGORY_AFFINITY.get(pkey, {}).get(opp.category, 0.0)
        val = (weight / 3) * affinity
        if val > best[0]:
            best = (val, pkey)
    prio_value = MAX["priority_alignment"] * best[0]
    criteria["priority_alignment"] = Criterion("priority_alignment", prio_value, MAX["priority_alignment"],
        f"Aligned with priority '{PRIORITIES[best[1]]['label']}' (weight {profile.priorities[best[1]]}/3)." if best[1] else "No company priority favours this category.")

    # 5. Timeliness
    t = timeliness(opp, today)
    t_value = {"open": 10, "closing_soon": 7, "upcoming": 8, "no_deadline": 4, "placeholder_rejected": 3, "date_unknown": 4 if t.get("recent") else 0, "closed": 0}[t["status"]]
    if t["status"] == "no_deadline" and opp.category in ("ecosystem_news", "business_programme", "testing_facility") and not t.get("recent"):
        t_value = 1
    criteria["timeliness"] = Criterion("timeliness", t_value, MAX["timeliness"], t["label"])

    # 6. Regional relevance — context-aware and gated by topical fit (never a substitute for relevance)
    topical = tech_value + dom_value + cap_value
    company_geo = profile.geo
    r_value, r_why, r_label = regional_relevance(company_geo, list(opp.geo_scopes or []), bool(opp.geo_inferred), opp.event_format,
                                                 opp.category, topical, profile.priorities.get("regional_focus", 1))
    criteria["regional_relevance"] = Criterion("regional_relevance", r_value, MAX["regional_relevance"], r_why)
    geography = {
        "scopes": list(opp.geo_scopes or []), "labels": [GEO_LABELS[s] for s in (opp.geo_scopes or []) if s in GEO_LABELS],
        "basis": opp.geo_basis, "inferred": bool(opp.geo_inferred), "format": opp.event_format, "format_basis": opp.format_basis,
        "relevance_label": r_label, "explanation": r_why, "company_location": company_geo.label if company_geo else None,
    }

    # 7. Evidence availability
    eq = evidence_quality(opp)
    e_value = {"high": 5, "medium": 3, "limited": 1}[eq["level"]]
    criteria["evidence_availability"] = Criterion("evidence_availability", e_value, MAX["evidence_availability"], eq["label"])

    # Penalties — guard against shallow overlap.
    penalties: list[dict] = []
    unmatched_strong_domains = [
        k for k, info in oc.items()
        if ALL_CONCEPTS.get(k) and ALL_CONCEPTS[k].kind == "domain" and ALL_CONCEPTS[k].specificity >= 0.8 and info["direct"]
        and info["weight"] >= 0.8 and not profile.has(k)
    ]
    if unmatched_strong_domains:
        amount = 10 if tech or topical_cap else 25
        penalties.append({"key": "domain_mismatch", "value": -amount,
                          "explanation": "Targets " + ", ".join(label(k) for k in unmatched_strong_domains[:2]) + ", which is not in the company profile."})
    total = sum(c.value for c in criteria.values()) + sum(p["value"] for p in penalties)
    specific = [k for k, *_ in (*tech, *topical_cap) if ALL_CONCEPTS[k].specificity >= 0.8]
    if not specific:
        cap_total = 30
        if total > cap_total:
            penalties.append({"key": "broad_overlap_only", "value": -(round(total - cap_total, 1)),
                              "explanation": "Only broad overlap (e.g. a shared sector word) — not enough to establish strong relevance."})
            total = cap_total
    if t["status"] == "closed":
        total = min(total, 10)
    score = int(round(max(0, min(100, total))))

    reasons: list[str] = []
    for c in (criteria["technology_fit"], criteria["industry_fit"], criteria["capability_fit"]):
        if c.value > 0:
            reasons.append(c.explanation)
    if best[1] and prio_value >= 3:
        reasons.append(criteria["priority_alignment"].explanation)
    if t["status"] in ("open", "closing_soon", "upcoming"):
        reasons.append(t["label"] + ".")
    if r_value >= 3:
        reasons.append(r_why)

    missing: list[str] = []
    if not opp.eligibility_text and opp.category not in ("event", "ecosystem_news"):
        missing.append("Specific eligibility conditions were not present in the collected record.")
    if opp.deadline_status == "placeholder_rejected":
        missing.append("The source contained a placeholder closing date, which VSP does not treat as a deadline.")
    elif opp.deadline_status == "not_stated" and opp.category not in ("ecosystem_news",):
        missing.append("No deadline or date is stated in the collected metadata.")
    if opp.category not in ("event", "ecosystem_news", "business_programme", "testing_facility") and not opp.funding_text:
        missing.append("Funding amount is not stated in the collected record.")
    if "metadata_only" in (opp.quality_flags or []):
        missing.append("Only title-level metadata was collected; details must be read on the source page.")
    if "english_title_missing" in (opp.quality_flags or []):
        missing.append("No English title in source; Swedish title shown.")

    requires_consortium = bool(opp.eligibility_text and CONSORTIUM_RE.search(opp.eligibility_text))
    top_cap = next((profile.claim_labels(k, 1)[0] for k, *_ in (*cap, *tech) if profile.claim_labels(k, 1)), None)
    is_actionable = t["status"] not in ("closed",) and not (opp.category == "event" and not t.get("recent")) and opp.category != "ecosystem_news"

    return MatchResult(
        opportunity_id=opp.id, score=score, band=band(score), criteria=list(criteria.values()), penalties=penalties,
        reasons=reasons, missing_information=missing, timeliness=t, evidence_quality=eq, completeness=completeness(opp),
        eligibility=eligibility(opp), business_value=business_value(opp, top_cap, tech, dom),
        next_action=next_action(opp, t, requires_consortium, top_cap), requires_consortium=requires_consortium,
        supporting_claim_ids=sorted(supporting), is_actionable=is_actionable, geography=geography,
    )


def business_value(opp: Opportunity, top_cap: str | None, tech: list, dom: list) -> str:
    focus = f" for work on {top_cap}" if top_cap else ""
    areas = ", ".join(label(k) for k, *_ in tech[:2]) or ", ".join(label(k) for k, *_ in dom[:1]) or "the company's field"
    if opp.category in ("funding_call", "innovation_programme"):
        amount = f" The source states: “{opp.funding_text}”" if opp.funding_text else " Funding amount is not stated in the collected record."
        return f"Potential co-financing{focus} within {areas}.{amount}"
    if opp.category in ("research_funding", "research_collaboration"):
        return f"Potential to fund research and development{focus} with partners, building knowledge in {areas}."
    if opp.category == "testing_facility":
        return f"Potential access to test or validation capacity relevant to {areas}{focus}."
    if opp.category == "event":
        return f"Networking and market intelligence in {areas}."
    if opp.category == "business_programme":
        return f"Business development support relevant to {areas}."
    return f"Ecosystem signal relevant to {areas}."


def next_action(opp: Opportunity, t: dict, consortium: bool, top_cap: str | None) -> str:
    if t["status"] == "closed":
        return "This opportunity has closed. Watch for a future round from the same programme."
    if opp.category in ("funding_call", "innovation_programme", "research_funding", "research_collaboration"):
        parts = []
        if opp.eligibility_text:
            parts.append("Read the source's 'who can apply' text and the call document to confirm eligibility")
        else:
            parts.append("Eligibility is not stated in the collected record — confirm it on the official call page first")
        if consortium:
            parts.append("the source text mentions multiple participants, so identify consortium partners early")
        if top_cap:
            parts.append(f"draft a one-page project idea building on '{top_cap}'")
        if t.get("days_left") is not None and t["status"] in ("open", "closing_soon"):
            parts.append(f"deadline in {t['days_left']} days")
        return "; ".join(parts) + "."
    if opp.category == "event":
        return "Open the event page to confirm the date and registration (event date is not in the collected metadata)."
    if opp.category == "testing_facility":
        return "Open the source and contact the organiser about access conditions, cost and availability."
    if opp.category == "business_programme":
        return "Open the source and check whether the programme accepts companies at your stage."
    return "Read the source for context; no action is implied."
