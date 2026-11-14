"""Natural-language search: deterministic parsing of a question into a structured query over VSP data.

The answer is always a list of database records with match explanations — never generated prose.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company
from app.services.intelligence.concepts import extract, label
from app.services.intelligence.taxonomy import ALL_CONCEPTS
from app.services.matching.opportunity_matching import RELEVANT_THRESHOLD

INTENTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("partners", re.compile(r"\b(compan(y|ies)|partners?|collaborat\w*|complementary|expertise|who can|organi[sz]ations?)\b", re.I)),
    ("technologies", re.compile(r"\b(technolog\w*|tech\b|improve|innovations? could)\b", re.I)),
    ("opportunities", re.compile(r"\b(fund\w*|grants?|calls?|opportunit\w*|programmes?|programs?|events?|research opportunit\w*|apply|deadlines?|test\w*|facilit\w*)\b", re.I)),
)
CATEGORY_HINTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("research", re.compile(r"\bresearch\b", re.I)),
    ("funding", re.compile(r"\b(fund\w*|grants?|financ\w*)\b", re.I)),
    ("event", re.compile(r"\b(events?|conferences?|meetups?)\b", re.I)),
    ("testing", re.compile(r"\b(test\w*|labs?|laborator\w*|facilit\w*)\b", re.I)),
)
CATEGORY_MAP = {
    "research": ("research_funding", "research_collaboration"),
    "funding": ("funding_call", "innovation_programme", "research_funding", "research_collaboration"),
    "event": ("event",),
    "testing": ("testing_facility",),
}


@dataclass
class ParsedQuery:
    text: str
    intent: str
    company_id: int | None
    company_name: str | None
    concepts: list[str]
    categories: list[str]
    notes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"text": self.text, "intent": self.intent, "company_id": self.company_id, "company_name": self.company_name,
                "concepts": [{"key": k, "label": label(k), "kind": ALL_CONCEPTS[k].kind} for k in self.concepts],
                "categories": self.categories, "notes": self.notes, "parser": "deterministic rules (no LLM)"}


def parse(db: Session, text: str, default_company_id: int | None = None) -> ParsedQuery:
    companies = list(db.scalars(select(Company).where(Company.profile_level.in_(("full", "partial")))))
    company = None
    lowered = text.lower()
    for c in sorted(companies, key=lambda c: -len(c.name)):
        names = {c.name.lower(), c.slug.replace("-", " ")}
        short = re.sub(r"\s*\(.*\)", "", c.name).lower()
        names.add(short)
        if any(n and re.search(rf"\b{re.escape(n)}\b", lowered) for n in names):
            company = c
            break
    notes = []
    if company is None and default_company_id:
        company = next((c for c in companies if c.id == default_company_id), None)
        if company:
            notes.append(f"No company named in the question; using the selected company ({company.name}).")
    # Concepts mentioned, excluding those that only come from the company name itself.
    concepts = [k for k, m in extract(text).items() if m.direct]
    scores = {intent: len(p.findall(text)) for intent, p in INTENTS}
    intent = max(scores, key=lambda k: (scores[k], k == "opportunities"))
    if scores[intent] == 0:
        intent = "opportunities" if company else "technologies"
        notes.append("Intent not explicit; defaulted based on the question.")
    categories: list[str] = []
    for hint, pattern in CATEGORY_HINTS:
        if pattern.search(text):
            categories.extend(c for c in CATEGORY_MAP[hint] if c not in categories)
    if intent == "opportunities" and "research" in lowered and "fund" not in lowered:
        categories = list(CATEGORY_MAP["research"])
    return ParsedQuery(text, intent, company.id if company else None, company.name if company else None, concepts, categories, notes)


def run(db: Session, text: str, default_company_id: int | None = None, viewer_id: int | None = None, public_only: bool = False) -> dict:
    from app.services.recommendations.pipeline import Workspace

    q = parse(db, text, default_company_id)
    if public_only and q.company_id is not None:
        q.notes.append(f"{q.company_name}'s workspace is private; showing results that do not depend on its private data.")
        q.company_id = None
    ws = Workspace(db)
    results: list[dict] = []

    if q.intent == "opportunities":
        if q.company_id and q.company_id in ws.profiles:
            for opp, m in ws.matches(q.company_id):
                if q.categories and opp.category not in q.categories:
                    continue
                if q.concepts and not any(k in (opp.concepts or {}) for k in q.concepts):
                    continue
                if m.score < RELEVANT_THRESHOLD - 10 or not m.is_actionable:
                    continue
                results.append({"type": "opportunity", "id": opp.id, "title": opp.title, "score": m.score, "band": m.band,
                                "subtitle": f"{opp.organisation} · {opp.category.replace('_', ' ')} · {m.timeliness['label']}",
                                "why": m.reasons[:3], "source_url": opp.source_url, "provenance": opp.provenance})
        else:
            for opp in ws.opps:
                hits = [k for k in q.concepts if k in (opp.concepts or {})]
                if (q.concepts and not hits) or (q.categories and opp.category not in q.categories):
                    continue
                if not q.concepts and not q.categories:
                    continue
                results.append({"type": "opportunity", "id": opp.id, "title": opp.title, "score": len(hits) * 25,
                                "subtitle": f"{opp.organisation} · {opp.category.replace('_', ' ')}",
                                "why": [f"Mentions {label(k)}: {', '.join(opp.concepts[k]['terms'][:2])}" for k in hits],
                                "source_url": opp.source_url, "provenance": opp.provenance})
    elif q.intent == "partners":
        if q.company_id and q.company_id in ws.profiles:
            intel = ws.intelligence(q.company_id)
            for r in intel.collaborations:
                if q.concepts and not any(r.partner.has(k) or any(f.offer_key == k or f.need_key == k for f in r.fired) for k in q.concepts):
                    continue
                results.append({"type": "company", "id": r.partner.company.id, "title": r.partner.company.name, "score": round(r.score),
                                "band": r.strength, "subtitle": f"Potential collaboration · {r.strength}",
                                "why": [f.as_dict()["rationale"] for f in r.fired[:2]]})
        else:
            for cid, profile in ws.public_profiles.items():
                hits = [k for k in q.concepts if profile.has(k)]
                if q.concepts and not hits:
                    continue
                strength = sum(profile.strength(k) for k in hits)
                results.append({"type": "company", "id": cid, "title": profile.company.name, "score": round(40 * strength),
                                "subtitle": f"{profile.company.profile_level} profile",
                                "why": [f"{label(k)}: {', '.join(profile.claim_labels(k, 2))}" for k in hits]
                                or ["Profiled ecosystem organisation"]})
    else:  # technologies
        target_ids = [q.company_id] if q.company_id else list(ws.profiles)
        for cid in target_ids:
            intel = ws.intelligence(cid)
            for t in intel.technologies:
                if q.concepts and t.key not in q.concepts and not any(
                    a["capability"] == label(k) for k in q.concepts for a in t.applications
                ) and not any(k in DOMAIN_TECH_KEYS(t.key) for k in q.concepts):
                    continue
                if t.ring == "monitor" and not q.concepts:
                    continue
                results.append({"type": "technology", "id": t.key, "title": label(t.key), "score": round(t.score),
                                "band": t.ring, "subtitle": f"{intel.profile.company.name} · ring: {t.ring} · {t.relation}",
                                "why": [c["explanation"] for c in t.contributions[:3]], "company_id": cid})
    results.sort(key=lambda r: -r["score"])
    return {"query": q.as_dict(), "results": results[:25], "count": len(results),
            "note": "Results are records from the VSP database ranked by the matching engine; no text was generated."}


def DOMAIN_TECH_KEYS(tech_key: str) -> set[str]:  # noqa: N802
    from app.services.intelligence.taxonomy import DOMAIN_TECH

    return {d for d, techs in DOMAIN_TECH.items() if tech_key in techs}
