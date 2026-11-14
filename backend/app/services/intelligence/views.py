"""Read models assembled from the matching engine: graph, comparison, overview and innovation brief."""
from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.clock import today, utcnow
from app.models import CollectionRun, Evidence, Recommendation, Source, SourceHealth
from app.services.intelligence.concepts import label
from app.services.intelligence.profile import CompanyProfileModel, claim_strength
from app.services.intelligence.taxonomy import ALL_CONCEPTS, CAPABILITY_KEYS, PRIORITIES
from app.services.matching.complementarity import DISCLAIMER, assess_pair, collaboration_detail
from app.services.matching.opportunity_matching import RELEVANT_THRESHOLD
from app.services.recommendations.pipeline import Workspace, summary_for

PROFILE_FIELDS_EXPECTED = ("overview", "product", "technology", "capability", "industry", "research_interest", "business_focus",
                           "project", "documented_collaboration", "location")


def completeness(profile: CompanyProfileModel) -> dict:
    present = {c.field for c in profile.effective_claims}
    fields = []
    for f in PROFILE_FIELDS_EXPECTED:
        claims = [c for c in profile.effective_claims if c.field == f]
        kinds = sorted({c.claim_type for c in claims})
        fields.append({"field": f, "count": len(claims), "types": kinds,
                       "status": "stated" if "source_stated" in kinds else ("user" if "user_provided" in kinds else ("inferred" if kinds else "unknown"))})
    filled = sum(1 for f in PROFILE_FIELDS_EXPECTED if f in present)
    return {"score_pct": round(100 * filled / len(PROFILE_FIELDS_EXPECTED)), "fields": fields,
            "unknown": [f for f in PROFILE_FIELDS_EXPECTED if f not in present]}


def graph(ws: Workspace, company_id: int, max_opps: int = 8) -> dict:
    intel = ws.intelligence(company_id)
    me = intel.profile.company
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def node(nid: str, kind: str, lbl: str, **data) -> None:  # noqa: ANN003
        nodes.setdefault(nid, {"id": nid, "type": kind, "label": lbl, "data": data})

    node(f"c{me.id}", "company", me.name, focus=True, company_id=me.id, profile_level=me.profile_level)
    for t in intel.technologies:
        if t.ring in ("adopt", "trial", "assess"):
            node(f"t:{t.key}", "technology", label(t.key), ring=t.ring, score=round(t.score), area=ALL_CONCEPTS[t.key].area)
            edges.append({"id": f"e:c{me.id}-t:{t.key}", "source": f"c{me.id}", "target": f"t:{t.key}", "kind": "technology",
                          "label": t.relation, "explanation": t.ring_rule + " " + (t.contributions[0]["explanation"] if t.contributions else "")})
    for cap in sorted(k for k in CAPABILITY_KEYS if intel.profile.has(k) and not intel.profile.support(k).via_interest_only)[:8]:
        node(f"k:{cap}:{me.id}", "capability", label(cap), owner=me.name, claims=intel.profile.claim_labels(cap, 2))
        edges.append({"id": f"e:c{me.id}-k:{cap}", "source": f"c{me.id}", "target": f"k:{cap}:{me.id}", "kind": "capability",
                      "label": "documented", "explanation": "Capability documented in: " + "; ".join(intel.profile.claim_labels(cap, 2))})
    for opp, m in [(o, m) for o, m in intel.matches if m.is_actionable and m.score >= RELEVANT_THRESHOLD and o.category != "ecosystem_news"][:max_opps]:
        node(f"o{opp.id}", "opportunity", opp.title, opportunity_id=opp.id, score=m.score, category=opp.category,
             deadline=opp.deadline_at.isoformat() if opp.deadline_at else None)
        edges.append({"id": f"e:c{me.id}-o{opp.id}", "source": f"c{me.id}", "target": f"o{opp.id}", "kind": "opportunity",
                      "label": f"relevance {m.score}", "explanation": " ".join(m.reasons[:2])})
        for key, info in (opp.concepts or {}).items():
            if f"t:{key}" in nodes and info.get("direct"):
                edges.append({"id": f"e:t:{key}-o{opp.id}", "source": f"t:{key}", "target": f"o{opp.id}", "kind": "mentions",
                              "label": "mentions", "explanation": f"Opportunity text mentions: {', '.join(info['terms'][:2])}"})
    for r in intel.collaborations:
        p = r.partner.company
        node(f"c{p.id}", "company", p.name, company_id=p.id, profile_level=p.profile_level, strength=r.strength, score=round(r.score))
        top = r.fired[0].as_dict()
        edges.append({"id": f"e:c{me.id}-c{p.id}", "source": f"c{me.id}", "target": f"c{p.id}", "kind": "potential_collaboration",
                      "label": f"potential · {r.strength}", "explanation": top["rationale"], "disclaimer": DISCLAIMER,
                      "rules": [f.rule.key for f in r.fired]})
        for so in r.shared_opportunities:
            if f"o{so['id']}" in nodes:
                edges.append({"id": f"e:c{p.id}-o{so['id']}", "source": f"c{p.id}", "target": f"o{so['id']}", "kind": "opportunity",
                              "label": f"relevance {so['partner_score']}", "explanation": f"Also relevant to {p.name}."})
        for f in r.fired[:2]:
            offer_owner = f.provider.company
            kid = f"k:{f.offer_key}:{offer_owner.id}"
            node(kid, "capability", label(f.offer_key), owner=offer_owner.name, claims=f.provider.claim_labels(f.offer_key, 2))
            edges.append({"id": f"e:c{offer_owner.id}-{kid}", "source": f"c{offer_owner.id}", "target": kid, "kind": "capability",
                          "label": "offers", "explanation": f"Documented by {offer_owner.name}: " + "; ".join(f.provider.claim_labels(f.offer_key, 2))})
    unique = {e["id"]: e for e in edges}
    return {"nodes": list(nodes.values()), "edges": list(unique.values()),
            "legend": {"company": "Organisation (profiled)", "technology": "Technology (radar ring adopt/trial/assess)",
                       "opportunity": f"Open opportunity with relevance ≥ {RELEVANT_THRESHOLD}", "capability": "Documented capability",
                       "potential_collaboration": "Potential complementarity — not an existing partnership"},
            "disclaimer": DISCLAIMER}


def compare(ws: Workspace, a_id: int, b_id: int, viewer_id: int | None = None) -> dict:
    """Compare two companies. Only the viewer's own private profile is used; the other side is public."""
    a = ws.profile(a_id, public=a_id != viewer_id)
    b = ws.profile(b_id, public=b_id != viewer_id)

    def keys(p: CompanyProfileModel, kind: str) -> set[str]:
        return {k for k, s in p.concepts.items() if ALL_CONCEPTS[k].kind == kind and not s.via_interest_only}

    def pack(ks: set[str], p: CompanyProfileModel | None = None) -> list[dict]:
        return [{"key": k, "label": label(k), **({"claims": p.claim_labels(k, 2)} if p else {})} for k in sorted(ks, key=label)]

    ma, mb = ws.match_map(a_id, public=a.public), ws.match_map(b_id, public=b.public)
    result = assess_pair(a, b, ma, mb, ws.opp_by_id)
    detail = collaboration_detail(a, result) if result else None
    joint = []
    for oid, m in ma.items():
        n = mb.get(oid)
        if n and m.is_actionable and m.score >= RELEVANT_THRESHOLD and n.score >= RELEVANT_THRESHOLD:
            o = ws.opp_by_id[oid]
            joint.append({"id": oid, "title": o.title, "a_score": m.score, "b_score": n.score, "requires_consortium": m.requires_consortium})
    joint.sort(key=lambda j: -(j["a_score"] + j["b_score"]))
    missing = []
    for p in (a, b):
        unknown = completeness(p)["unknown"]
        if unknown:
            missing.append({"company": p.company.name, "unknown_fields": unknown})
    return {
        "a": {"id": a.company.id, "name": a.company.name, "profile_level": a.company.profile_level},
        "b": {"id": b.company.id, "name": b.company.name, "profile_level": b.company.profile_level},
        "shared_capabilities": pack(keys(a, "capability") & keys(b, "capability")),
        "shared_technologies": pack(keys(a, "technology") & keys(b, "technology")),
        "shared_industries": pack(keys(a, "domain") & keys(b, "domain")),
        "only_a_technologies": pack(keys(a, "technology") - keys(b, "technology"), a),
        "only_b_technologies": pack(keys(b, "technology") - keys(a, "technology"), b),
        "only_a_capabilities": pack(keys(a, "capability") - keys(b, "capability"), a),
        "only_b_capabilities": pack(keys(b, "capability") - keys(a, "capability"), b),
        "complementarity": detail,
        "joint_opportunities": joint[:6],
        "missing_information": missing,
        "note": "Shared areas show similarity; only the complementarity section reflects collaboration potential." if detail
        else "No complementarity rule fired. Similarity alone is not treated as collaboration potential.",
    }


def data_freshness(db: Session) -> dict:
    rows = db.execute(select(Source, SourceHealth).join(SourceHealth, SourceHealth.source_id == Source.id)).all()
    last_live = max((h.last_success_at for _s, h in rows if h.last_success_at), default=None)
    last_run = db.scalar(select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(1))
    snapshot_ts = db.scalar(select(Evidence.retrieved_at).order_by(Evidence.retrieved_at.desc()).limit(1))
    modes = sorted({h.data_mode for s, h in rows if s.collectable and s.enabled})
    return {
        "last_live_collection": last_live.isoformat() if last_live else None,
        "last_collection_attempt": last_run.started_at.isoformat() if last_run else None,
        "latest_record_retrieved_at": snapshot_ts.isoformat() if snapshot_ts else None,
        "data_modes": modes,
        "label": "Live data collected" if "live" in modes and len(modes) == 1 else
                 ("Mixed: some sources live, some from snapshot" if "live" in modes else "Previously collected snapshot (not live)"),
        "sources": [{"key": s.key, "name": s.name, "status": h.status, "data_mode": h.data_mode,
                     "last_success_at": h.last_success_at.isoformat() if h.last_success_at else None}
                    for s, h in rows if s.collectable],
    }


def overview(db: Session, ws: Workspace, company_id: int) -> dict:
    intel = ws.intelligence(company_id)
    p = intel.profile
    recs = list(db.scalars(select(Recommendation).where(Recommendation.company_id == company_id, Recommendation.is_current.is_(True),
                                                        Recommendation.status != "dismissed").order_by(Recommendation.rank_position)))
    relevant = [(o, m) for o, m in intel.matches if m.is_actionable and m.score >= RELEVANT_THRESHOLD and o.category != "ecosystem_news"]
    deadlines = sorted([(o, m) for o, m in relevant if o.deadline_at and m.timeliness["status"] in ("open", "closing_soon", "upcoming")],
                       key=lambda om: om[0].deadline_at)
    claims = p.effective_claims
    by_type = {t: sum(1 for c in claims if c.claim_type == t) for t in ("source_stated", "inferred", "user_provided")}
    return {
        "company": {"id": p.company.id, "name": p.company.name, "tagline": p.company.tagline, "website": p.company.website,
                    "membership_status": p.company.membership_status, "profile_level": p.company.profile_level},
        "summary": summary_for(ws, company_id),
        "profile": {"claims_by_type": by_type, "completeness": completeness(p)["score_pct"],
                    "overview": next((c.value for c in claims if c.field == "overview"), None),
                    "pending_review": sum(1 for c in claims if c.claim_type == "inferred" and c.status == "active")},
        "metrics": {
            "relevant_opportunities": len(relevant),
            "opportunities_considered": len(intel.matches),
            "technologies_adopt_trial": sum(1 for t in intel.technologies if t.ring in ("adopt", "trial")),
            "potential_partners": sum(1 for r in intel.collaborations if r.score >= 25),
            "high_priority_actions": sum(1 for r in recs if r.priority_tier == "high"),
        },
        "top_opportunities": [{"id": o.id, "title": o.title, "score": m.score, "band": m.band, "category": o.category,
                               "timeliness": m.timeliness, "organisation": o.organisation} for o, m in relevant[:5]],
        "technologies": [{"key": t.key, "name": label(t.key), "ring": t.ring, "score": round(t.score), "relation": t.relation}
                         for t in intel.technologies if t.ring in ("adopt", "trial")][:6],
        "partners": [{"id": r.partner.company.id, "name": r.partner.company.name, "score": round(r.score), "strength": r.strength,
                      "headline": r.fired[0].as_dict()["rationale"]} for r in intel.collaborations if r.score >= 25][:4],
        "top_recommendations": [{"id": r.id, "title": r.title, "tier": r.priority_tier, "kind": r.kind, "rank_score": r.rank_score,
                                 "status": r.status} for r in recs[:5]],
        "deadlines": [{"id": o.id, "title": o.title, "deadline_at": o.deadline_at.isoformat(), "days_left": m.timeliness.get("days_left"),
                       "score": m.score} for o, m in deadlines[:8]],
        "freshness": data_freshness(db),
    }


def innovation_brief(db: Session, ws: Workspace, company_id: int) -> dict:
    from app.services.llm.adapter import polish_summary

    intel = ws.intelligence(company_id)
    p = intel.profile
    recs = list(db.scalars(select(Recommendation).where(Recommendation.company_id == company_id, Recommendation.is_current.is_(True),
                                                        Recommendation.status != "dismissed").order_by(Recommendation.rank_position)))
    relevant = [(o, m) for o, m in intel.matches if m.is_actionable and m.score >= RELEVANT_THRESHOLD and o.category != "ecosystem_news"][:6]
    evidence_ids: set[int] = set()
    profile_section = []
    for f in ("overview", "product", "technology", "capability", "industry"):
        for c in [c for c in p.effective_claims if c.field == f][:4]:
            profile_section.append({"field": f, "label": c.label, "value": c.value, "claim_type": c.claim_type, "evidence_id": c.evidence_id})
            if c.evidence_id:
                evidence_ids.add(c.evidence_id)
    opportunities = []
    for o, m in relevant:
        opportunities.append({"id": o.id, "title": o.title, "organisation": o.organisation, "score": m.score, "band": m.band,
                              "deadline": o.deadline_at.date().isoformat() if o.deadline_at else "Not stated in source",
                              "why": m.reasons[:2], "eligibility": m.eligibility["note"], "source_url": o.source_url,
                              "evidence_id": o.evidence_id})
        if o.evidence_id:
            evidence_ids.add(o.evidence_id)
    techs = [{"name": label(t.key), "ring": t.ring, "relation": t.relation, "next_step": t.next_step,
              "application": t.applications[0]["application"] if t.applications else None}
             for t in intel.technologies if t.ring in ("adopt", "trial", "assess")][:6]
    partners = []
    for r in intel.collaborations[:4]:
        d = collaboration_detail(p, r)
        partners.append({"name": r.partner.company.name, "strength": r.strength, "why": d["why"][:1], "scenario": d["scenario"],
                         "first_step": d["first_step"]})
    actions = [{"tier": r.priority_tier, "title": r.title, "next_step": r.detail.get("next_step"), "rank_score": r.rank_score} for r in recs[:8]]
    evidence = [
        {"id": e.id, "title": e.title, "publisher": e.publisher, "url": e.url, "retrieved_at": e.retrieved_at.date().isoformat(),
         "provenance": e.provenance, "type": e.evidence_type}
        for e in db.scalars(select(Evidence).where(Evidence.id.in_(evidence_ids)).order_by(Evidence.publisher, Evidence.id))
    ]
    limitations = [
        "Relevance scores are heuristic and explainable; they are not probabilities of success.",
        "VSP does not assess funding eligibility. Eligibility text, when shown, is quoted from the source.",
        "Collaboration suggestions are potential complementarities derived from public information; no partner has been contacted.",
        "Rule-based inferences are labelled and should be confirmed by the company.",
    ]
    fresh = data_freshness(db)
    if "live" not in fresh["data_modes"]:
        limitations.append("Opportunity data comes from a previously collected snapshot, not a live collection.")
    if any(c.claim_type == "inferred" and c.status == "active" for c in p.effective_claims):
        limitations.append("The profile contains unconfirmed inferred interests that influence some results.")
    return {
        "title": f"Innovation brief — {p.company.name}",
        "generated_at": utcnow().isoformat(timespec="seconds"),
        "as_of": today().isoformat(),
        "company": {"name": p.company.name, "website": p.company.website, "membership_status": p.company.membership_status},
        "executive_summary": polish_summary(summary_for(ws, company_id)),
        "profile": profile_section,
        "opportunities": opportunities,
        "technologies": techs,
        "partners": partners,
        "actions": actions,
        "evidence": evidence,
        "limitations": limitations,
        "data_freshness": fresh["label"],
    }


# ----------------------------------------------------------------------------- small-company focus view
NEW_WINDOW_DAYS = 45


def _days_ago(dt) -> int | None:  # noqa: ANN001
    return (today() - dt.date()).days if dt else None


def focus(db: Session, ws: Workspace, company_id: int) -> dict:
    """'Your Innovation Opportunities': a short, actionable page for a 10–25 person company."""
    from app.models import SavedRecommendation

    intel = ws.intelligence(company_id)
    p = intel.profile
    recs = list(db.scalars(select(Recommendation).where(Recommendation.company_id == company_id, Recommendation.is_current.is_(True),
                                                        Recommendation.status.in_(("open", "saved"))).order_by(Recommendation.rank_position)))
    # Same order as the Recommendation Centre: tier first (evidence rules), then rank.
    recs.sort(key=lambda r: ({"high": 0, "medium": 1, "later": 2}[r.priority_tier], r.rank_position))
    opp_by_id = ws.opp_by_id

    def link_for(r: Recommendation) -> dict | None:
        if r.related_opportunity_id and r.related_opportunity_id in opp_by_id:
            o = opp_by_id[r.related_opportunity_id]
            return {"label": f"Open source ({o.organisation})", "url": o.apply_url or o.source_url}
        if r.related_company_id:
            partner = next((x.partner.company for x in intel.collaborations if x.partner.company.id == r.related_company_id), None)
            if partner and partner.website:
                return {"label": f"{partner.name} website", "url": partner.website}
        return None

    top3 = []
    for r in recs[:3]:
        geo = None
        if r.related_opportunity_id:
            m = ws.match_map(company_id).get(r.related_opportunity_id)
            geo = m.geography if m else None
        elif r.related_company_id:
            geo = (r.detail.get("collaboration") or {}).get("location")
        top3.append({"id": r.id, "title": r.title, "tier": r.priority_tier, "kind": r.kind, "status": r.status,
                     "why": (r.detail.get("why") or [])[:2], "next_step": r.detail.get("next_step"),
                     "source": link_for(r), "geography": geo})

    relevant = [(o, m) for o, m in intel.matches if m.is_actionable and m.score >= RELEVANT_THRESHOLD]
    deadlines = sorted([(o, m) for o, m in relevant if o.deadline_at and m.timeliness["status"] in ("open", "closing_soon", "upcoming")],
                       key=lambda om: om[0].deadline_at)[:5]
    new = [(o, m) for o, m in relevant
           if (_days_ago(o.opens_at) is not None and 0 <= _days_ago(o.opens_at) <= NEW_WINDOW_DAYS)
           or (_days_ago(o.published_at) is not None and 0 <= _days_ago(o.published_at) <= NEW_WINDOW_DAYS)][:5]
    local = [(o, m) for o, m in intel.matches
             if o.category in ("event", "testing_facility", "business_programme") and m.score >= 20 and m.is_actionable
             and ("blekinge" in (o.geo_scopes or []) or o.event_format == "online")]
    local.sort(key=lambda om: -om[1].score)

    def opp_card(o, m) -> dict:  # noqa: ANN001
        return {"id": o.id, "title": o.title, "organisation": o.organisation, "category": o.category, "score": m.score, "band": m.band,
                "deadline_at": o.deadline_at.isoformat() if o.deadline_at else None, "days_left": m.timeliness.get("days_left"),
                "timeliness": m.timeliness["label"], "geography": m.geography, "url": o.apply_url or o.source_url,
                "why": m.reasons[:1]}

    nearby, wider = [], []
    for r in intel.collaborations:
        if r.score < 25:
            continue
        d = collaboration_detail(p, r)
        card = {"id": r.partner.company.id, "name": r.partner.company.name, "score": round(r.score), "strength": r.strength,
                "location": d["location"], "proximity": d["proximity"]["explanation"], "why": d["why"][:1], "first_step": d["first_step"],
                "website": r.partner.company.website}
        (nearby if d["location"] and "blekinge" in d["location"]["scopes"] else wider).append(card)
    saved = [{"id": r.id, "title": r.title, "kind": r.kind} for r in recs if r.status == "saved"]
    saved_count = db.scalar(select(func.count(SavedRecommendation.id)).where(SavedRecommendation.company_id == company_id)) or 0
    sources_used = sorted({o.source.name for o in ws.opps if o.source})
    return {
        "company": {"id": p.company.id, "name": p.company.name, "location": p.geo.as_dict() if p.geo else None},
        "time_saved": {
            "opportunities_screened": len(ws.opps), "sources": sources_used, "relevant": len(relevant),
            "message": f"VSP screened {len(ws.opps)} records from {len(sources_used)} sources; {len(relevant)} are worth your time.",
        },
        "top_three": top3,
        "deadlines": [opp_card(o, m) for o, m in deadlines],
        "new_opportunities": [opp_card(o, m) for o, m in new],
        "local_events": [opp_card(o, m) for o, m in local[:5]],
        "regional_partners": nearby[:3],
        "wider_partners": wider[:2],
        "technologies": [{"key": t.key, "name": label(t.key), "ring": t.ring, "next_step": t.next_step}
                         for t in intel.technologies if t.ring in ("adopt", "trial") and t.relation != "core"][:2],
        "saved": saved, "saved_count": saved_count,
        "priorities": [{"key": k, **v, "weight": p.priorities.get(k, 1)} for k, v in PRIORITIES.items()],
        "freshness": data_freshness(db)["label"],
    }


# ----------------------------------------------------------------------------- unified funding discovery
FUNDING_CATEGORIES = ("funding_call", "innovation_programme", "research_funding", "research_collaboration", "business_programme")


def dedupe_key(title: str, deadline) -> str:  # noqa: ANN001
    import re as _re

    norm = _re.sub(r"[^a-z0-9åäö]+", " ", title.lower()).strip()
    norm = _re.sub(r"\b(20\d\d|call|utlysning|round)\b", " ", norm)
    return f"{' '.join(norm.split())}|{deadline.date().isoformat() if deadline else '-'}"


def dedupe_funding(items: list[dict]) -> list[dict]:
    """Merge the same opportunity listed by several sources, keeping every original source link."""
    merged: dict[str, dict] = {}
    for it in items:
        key = it["dedupe_key"]
        if key in merged:
            merged[key]["also_listed_by"].append({"source": it["source_name"], "url": it["url"]})
        else:
            merged[key] = {**it, "also_listed_by": []}
    return list(merged.values())


def funding_discovery(db: Session, ws: Workspace, company_id: int) -> dict:
    from app.services.collectors.registry import SOURCES

    rows = []
    for o, m in ws.matches(company_id):
        if o.category not in FUNDING_CATEGORIES or not m.is_actionable:
            continue
        rows.append({"id": o.id, "title": o.title, "organisation": o.organisation, "programme": o.programme, "category": o.category,
                     "score": m.score, "band": m.band, "deadline_at": o.deadline_at.isoformat() if o.deadline_at else None,
                     "deadline_status": o.deadline_status, "timeliness": m.timeliness, "eligibility": m.eligibility,
                     "geography": m.geography, "source_name": o.source.name if o.source else None, "provenance": o.provenance,
                     "url": o.source_url, "apply_url": o.apply_url, "dedupe_key": dedupe_key(o.title, o.deadline_at)})
    items = dedupe_funding(rows)
    sources = []
    for d in SOURCES:
        if d.key in ("vinnova", "ymner", "eu_funding_tenders"):
            sources.append({"key": d.key, "name": d.name, "integrated": d.enabled, "reason": d.disabled_reason,
                            "link": d.extra.get("external_link") or d.base_url, "note": d.license_note})
    return {"items": items, "relevant": [i for i in items if i["score"] >= RELEVANT_THRESHOLD], "sources": sources,
            "note": "Funding from integrated sources is ranked for your company. External services are linked, not scraped."}


def member_directory(db: Session) -> dict:
    from app.models import Company

    companies = list(db.scalars(select(Company).order_by(Company.is_demo_company.desc(), Company.name)))
    out = []
    for c in companies:
        ev = c.membership_evidence
        geo = build_public_geo(c)
        out.append({"id": c.id, "name": c.name, "slug": c.slug, "profile_level": c.profile_level, "organisation_type": c.organisation_type,
                    "membership_status": c.membership_status, "membership_url": ev.url if ev else None,
                    "membership_retrieved_at": ev.retrieved_at.isoformat() if ev else None,
                    "membership_provenance": ev.provenance if ev else None, "location": geo, "has_workspace": c.profile_level in ("full", "partial"),
                    "is_demo_company": c.is_demo_company, "website": c.website})
    verified = sum(1 for c in companies if c.membership_status == "verified")
    return {"items": out, "total": len(out), "verified_members": verified,
            "profile_levels": {lvl: sum(1 for c in companies if c.profile_level == lvl) for lvl in ("full", "partial", "directory")},
            "note": "Membership verified against the Blue Science Park member directory (name, link, date only). "
                    "Directory-only members have no VSP profile yet: no capabilities are inferred for them."}


def build_public_geo(company) -> dict:  # noqa: ANN001
    from app.services.intelligence.profile import build_profile

    return build_profile(company, public=True).geo.as_dict()
