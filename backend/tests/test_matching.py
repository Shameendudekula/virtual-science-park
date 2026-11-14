"""Matching behaviour on the real seeded data (requirements 1-6, 8)."""
from __future__ import annotations

import re

from app.core.clock import today
from app.models import Company, CompanyClaim, Opportunity
from app.services.intelligence.profile import build_profile
from app.services.matching.complementarity import assess_pair
from app.services.matching.opportunity_matching import RELEVANT_THRESHOLD, score_opportunity
from app.services.matching.tagging import opportunity_concepts
from app.services.recommendations.pipeline import Workspace
from tests.conftest import company_id


def _ranked(db, slug):
    ws = Workspace(db)
    return ws, ws.matches(company_id(db, slug))


def _by_title(matches, fragment):
    return next((o, m) for o, m in matches if fragment.lower() in o.title.lower())


def test_ocean_harvesting_gets_energy_opportunities(seeded, db):
    _ws, matches = _ranked(db, "ocean-harvesting")
    actionable = [(o, m) for o, m in matches if m.is_actionable and o.category != "ecosystem_news"]
    top_titles = [o.title for o, _ in actionable[:3]]
    assert any("energy" in t.lower() for t in top_titles), top_titles
    opp, m = _by_title(matches, "Industrial flexible energy control")
    assert m.score >= 55 and m.band == "strong"
    tech = next(c for c in m.criteria if c.key == "technology_fit")
    assert "Energy Systems" in tech.explanation
    # Reasons trace back to source-stated claims of the company.
    claims = {c["claim_type"] for row in tech.matches for c in row["company_claims"]}
    assert "source_stated" in claims


def test_cleura_gets_cloud_and_cyber_results(seeded, db):
    ws, matches = _ranked(db, "cleura")
    actionable = [(o, m) for o, m in matches if m.is_actionable and o.category != "ecosystem_news"]
    assert actionable[0][0].title == "Cybersecurity, AI and resilience"
    intel = ws.intelligence(company_id(db, "cleura"))
    rings = {t.key: t.ring for t in intel.technologies}
    assert rings["cybersecurity"] == "adopt"
    assert rings["cloud_computing"] in ("adopt", "trial")
    # Energy-specific calls are not strong matches for a cloud company.
    _o, energy = _by_title(matches, "Industrial flexible energy control")
    assert energy.score < RELEVANT_THRESHOLD


def test_roxtec_gets_industrial_and_materials_results(seeded, db):
    ws, matches = _ranked(db, "roxtec")
    _o, mfg = _by_title(matches, "Advanced Manufacturing")
    assert mfg.score >= 40
    intel = ws.intelligence(company_id(db, "roxtec"))
    rel = {t.key: t.relation for t in intel.technologies}
    assert rel["advanced_materials"] == "core"
    partners = {r.partner.company.slug: [f.rule.key for f in r.fired] for r in intel.collaborations}
    assert "offshore_sealing" in partners["ocean-harvesting"]


def test_three_companies_get_materially_different_results(seeded, db):
    tops = {}
    for slug in ("ocean-harvesting", "cleura", "roxtec"):
        _ws, matches = _ranked(db, slug)
        tops[slug] = [o.id for o, m in matches if m.is_actionable and m.score >= RELEVANT_THRESHOLD][:5]
    assert tops["cleura"][0] != tops["ocean-harvesting"][0]
    assert set(tops["cleura"]) != set(tops["roxtec"])


def test_irrelevant_opportunities_rank_lower(seeded, db):
    _ws, matches = _ranked(db, "ocean-harvesting")
    _o, relevant = _by_title(matches, "Industrial flexible energy control")
    for fragment in ("life science", "food systems"):
        _o2, irrelevant = _by_title(matches, fragment)
        assert irrelevant.score < 20, (fragment, irrelevant.score)
        assert irrelevant.score < relevant.score
        assert any(p["key"] == "domain_mismatch" for p in irrelevant.penalties) or irrelevant.score < 10


def _synthetic(db, **fields) -> Opportunity:
    src = db.query(Opportunity).first().source
    o = Opportunity(source_id=src.id, external_id="synthetic", category=fields.pop("category", "funding_call"), organisation="Test",
                    source_url="https://data.vinnova.se/api/ansokningsomgangar/0000-00000", provenance="demo",
                    retrieved_at=fields.pop("retrieved_at", None) or db.query(Opportunity).first().retrieved_at,
                    content_hash="x", deadline_status="not_stated", quality_flags=[], **fields)
    o.id = -1
    o.concepts = opportunity_concepts(o)
    return o


def _tokens(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-zåäö]{4,}", text.lower())}


def test_shared_keywords_alone_do_not_establish_relevance(seeded, db):
    oh = db.query(Company).filter_by(slug="ocean-harvesting").one()
    profile = build_profile(oh)
    opp = _synthetic(db, title="Advanced systems for sustainable health innovation",
                     description="Advanced digital systems for a sustainable future in healthcare, with high efficiency and low cost.")
    company_text = " ".join(c.value for c in profile.effective_claims)
    shared = _tokens(opp.title + " " + opp.description) & _tokens(company_text)
    assert len(shared) >= 3, shared  # plenty of shared words ...
    m = score_opportunity(profile, opp, today())
    assert m.score < 20, m.score  # ... but no meaningful relevance
    assert any(p["key"] == "domain_mismatch" for p in m.penalties)


def test_broad_sector_overlap_is_capped(seeded, db):
    profile = build_profile(db.query(Company).filter_by(slug="ocean-harvesting").one())
    opp = _synthetic(db, title="Energy industry innovation 2026", description="Support for companies in the energy industry.")
    m = score_opportunity(profile, opp, today())
    assert m.score <= 30
    assert m.band in ("weak", "low")


def _profile(name: str, claims: list[tuple[str, str]]) -> object:
    c = Company(id=hash(name) % 100000, slug=name.lower(), name=name, profile_level="full")
    c.claims = [CompanyClaim(id=i + 1, field=f, value=v, label=v[:40], claim_type="source_stated", status="active", evidence_id=1)
                for i, (f, v) in enumerate(claims)]
    c.priorities = []
    return build_profile(c)


def test_complementary_capabilities_create_collaboration_suggestion():
    marine = _profile("WaveCo", [("product", "Floating buoy with mooring line for a wave energy converter tested in sea trials.")])
    sealer = _profile("SealCo", [("product", "Certified cable transit and pipe penetration sealing for offshore applications.")])
    result = assess_pair(marine, sealer)
    assert result is not None
    assert "offshore_sealing" in [f.rule.key for f in result.fired]
    assert result.fired[0].as_dict()["need"]["claims"], "the need must cite the seeker's claims"


def test_similarity_alone_creates_no_collaboration():
    a = _profile("CloudA", [("product", "OpenStack public cloud with virtual machines and kubernetes.")])
    b = _profile("CloudB", [("product", "Private cloud and IaaS on OpenStack for enterprises.")])
    assert assess_pair(a, b) is None


def test_missing_eligibility_is_communicated(seeded, db):
    profile = build_profile(db.query(Company).filter_by(slug="ocean-harvesting").one())
    opp = _synthetic(db, title="Wave energy pilot call", description="Funding for wave power demonstration.")
    m = score_opportunity(profile, opp, today())
    assert m.eligibility["status"] == "not_stated"
    assert "Not stated in source" in m.eligibility["note"]
    assert any("eligibility" in x.lower() for x in m.missing_information)
    stated = db.query(Opportunity).filter(Opportunity.eligibility_text.is_not(None)).first()
    m2 = score_opportunity(profile, stated, today())
    assert m2.eligibility["status"] == "source_text_available"
    assert "does not assess" in m2.eligibility["note"]


def test_scores_are_not_presented_as_probabilities(seeded, db):
    profile = build_profile(db.query(Company).filter_by(slug="cleura").one())
    m = score_opportunity(profile, db.query(Opportunity).first(), today())
    d = m.as_dict()
    assert "not a probability" in d["score_note"]
    assert set(d) >= {"relevance_score", "evidence_quality", "completeness", "eligibility"}
    assert sum(c["value"] for c in d["criteria"]) + sum(p["value"] for p in d["penalties"]) >= d["relevance_score"] - 1


def test_need_markers_are_not_topical_matches(seeded, db):
    """Regression: 'validation' in an unrelated test-facility call must not count as a topical match."""
    profile = build_profile(db.query(Company).filter_by(slug="ocean-harvesting").one())
    chips = _synthetic(db, title="Testing and validation of new semiconductor technology in pilot lines", category="testing_facility",
                       description="Pilot lines for validating new semiconductor chips.")
    marine = _synthetic(db, title="New environment to test marine technology at sea", category="testing_facility",
                        description="Test bed for offshore and marine technology validation.")
    mc, mm = score_opportunity(profile, chips, today()), score_opportunity(profile, marine, today())
    cap = lambda m: next(c for c in m.criteria if c.key == "capability_fit").value  # noqa: E731
    assert mc.score < RELEVANT_THRESHOLD and cap(mc) == 0
    assert cap(mm) > 0 and mm.score > mc.score
