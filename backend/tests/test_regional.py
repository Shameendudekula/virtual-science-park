"""Regional intelligence (Blue Science Park partner feedback). Synthetic records are test fixtures only."""
from __future__ import annotations

from app.core.clock import today
from app.models import Company, CompanyClaim, Opportunity
from app.services.intelligence.geography import company_geo, opportunity_geo
from app.services.intelligence.profile import build_profile
from app.services.matching.complementarity import assess_pair
from app.services.matching.opportunity_matching import score_opportunity
from app.services.matching.tagging import opportunity_concepts, tag_geography


def _opp(db, *, title, organisation="Test organiser", category="event", description=None) -> Opportunity:
    ref = db.query(Opportunity).first()
    o = Opportunity(source_id=ref.source_id, external_id=title, title=title, description=description, category=category,
                    organisation=organisation, source_url="https://example.invalid/test", provenance="demo",
                    retrieved_at=ref.retrieved_at, content_hash="x", deadline_status="not_stated", quality_flags=[],
                    published_at=ref.retrieved_at)
    o.id = -abs(hash(title)) % 10_000_000
    o.concepts = opportunity_concepts(o)
    tag_geography(o)
    return o


def _oh(db):
    return build_profile(db.query(Company).filter_by(slug="ocean-harvesting").one())


def _regional(m):
    return next(c for c in m.criteria if c.key == "regional_relevance")


TOPIC = "Wave energy and offshore renewable energy: buoy, mooring and power take-off engineering"


def test_company_location_comes_from_cited_claims(seeded, db):
    p = _oh(db)
    assert p.geo.verified and "karlskrona" in p.geo.scopes and "blekinge" in p.geo.scopes
    loc_claims = [c for c in p.claims if c.id in p.geo.claim_ids]
    assert loc_claims and all(c.claim_type == "source_stated" and c.evidence_id for c in loc_claims)


def test_physical_karlskrona_event_beats_same_event_elsewhere_in_sweden(seeded, db):
    p = _oh(db)
    local = _opp(db, title="Wave energy meetup in Karlskrona", description=TOPIC)
    sweden = _opp(db, title="Wave energy meetup in Gothenburg", description=TOPIC)
    assert local.geo_scopes[:2] == ["karlskrona", "blekinge"] and not local.geo_inferred
    assert sweden.geo_scopes == ["sweden"]
    ml, ms = score_opportunity(p, local, today()), score_opportunity(p, sweden, today())
    assert _regional(ml).value > _regional(ms).value
    assert ml.score > ms.score
    assert "practical to attend" in _regional(ml).explanation
    assert "travel" in _regional(ms).explanation


def test_international_webinar_is_not_penalised_for_location(seeded, db):
    p = _oh(db)
    webinar = _opp(db, title="International webinar: wave energy control (online, hosted in Rotterdam)", description=TOPIC)
    sweden = _opp(db, title="Wave energy meetup in Gothenburg", description=TOPIC)
    assert webinar.event_format == "online"
    mw, ms = score_opportunity(p, webinar, today()), score_opportunity(p, sweden, today())
    assert _regional(mw).value >= _regional(ms).value
    assert "location does not reduce relevance" in _regional(mw).explanation


def test_european_funding_is_not_excluded_for_being_outside_the_region(seeded, db):
    p = _oh(db)
    eu = _opp(db, title="Horizon Europe call: wave energy demonstration in European waters", category="funding_call",
              organisation="European Commission", description=TOPIC)
    national = _opp(db, title="National call: wave energy demonstration in Sweden", category="funding_call", organisation="Vinnova",
                    description=TOPIC)
    me, mn = score_opportunity(p, eu, today()), score_opportunity(p, national, today())
    assert "europe" in eu.geo_scopes
    assert _regional(me).value == _regional(mn).value  # neither is disadvantaged
    assert me.band in ("strong", "moderate")
    assert "not penalised" in _regional(me).explanation


def test_proximity_never_substitutes_for_relevance(seeded, db):
    p = _oh(db)
    unrelated_local = _opp(db, title="Hairdressing trade fair in Karlskrona", description="Hair styling products and salon services.")
    m = score_opportunity(p, unrelated_local, today())
    assert _regional(m).value < 1.0
    assert m.score < 20


def test_regional_priority_changes_local_weight(seeded, db):
    company = db.query(Company).filter_by(slug="ocean-harvesting").one()
    local = _opp(db, title="Wave energy meetup in Karlskrona", description=TOPIC)
    p = build_profile(company)
    p.priorities["regional_focus"] = 0
    low = _regional(score_opportunity(p, local, today())).value
    p.priorities["regional_focus"] = 3
    high = _regional(score_opportunity(p, local, today())).value
    assert high > low


def _profile(name, claims):
    c = Company(id=abs(hash(name)) % 100000, slug=name.lower(), name=name, profile_level="full", membership_status="verified")
    c.claims = [CompanyClaim(id=i + 1, field=f, value=v, label=v[:60], claim_type="source_stated", status="active", evidence_id=1)
                for i, (f, v) in enumerate(claims)]
    c.priorities = []
    return build_profile(c)


SEAL = ("product", "Certified cable transit and pipe penetration sealing for offshore applications.")


def test_nearby_complementary_partner_ranks_above_identical_partner_abroad(seeded, db):
    oh = _oh(db)
    near = _profile("SealNear", [SEAL, ("location", "Headquarters in Karlskrona, Sweden.")])
    far = _profile("SealFar", [SEAL, ("location", "Headquarters in Hamburg, Germany.")])
    rn, rf = assess_pair(oh, near), assess_pair(oh, far)
    assert rn and rf
    assert rn.score > rf.score
    assert "Blekinge" in rn.proximity["explanation"]


def test_distant_but_highly_relevant_partner_is_still_recommended(seeded, db):
    oh = _oh(db)
    distant = _profile("CableAndSealFar", [SEAL, ("capability", "High-voltage power cable systems and submarine cable-laying."),
                                           ("location", "Headquarters in Oslo, Norway.")])
    r = assess_pair(oh, distant)
    assert r is not None and r.score >= 25
    assert len(r.fired) >= 2


def test_nearby_company_with_only_superficial_similarity_is_not_suggested(seeded, db):
    oh = _oh(db)
    local_similar = _profile("LocalEnergyNews", [("overview", "Energy news and renewable energy blog for Sweden."),
                                                 ("location", "Office in Karlskrona, Blekinge.")])
    assert assess_pair(oh, local_similar) is None


def test_bsp_event_location_is_labelled_as_inferred(seeded, db):
    g = opportunity_geo(organisation="Blue Science Park", category="event", title="DigIT Hub Sweden Day", text="")
    assert g.inferred and "blekinge" in g.scopes and "venue not stated" in g.basis
    assert g.event_format == "unknown"


def test_unverified_member_gets_no_proximity_credit():
    geo = company_geo([], membership_verified=True)
    assert not geo.verified and geo.scopes == [] and "not verified" in geo.label
