"""Regional intelligence: geographic scopes and event format, each with an explicit basis (stated vs inferred).

Scopes: karlskrona ⊂ blekinge ⊂ sweden ⊂ europe, plus international and online.
Regional relevance is context-aware:
  * physical events / facilities / programmes: nearby (Blekinge) is a practical advantage;
  * online formats: location never reduces relevance;
  * funding: geography describes the programme's area, not travel; national/European calls are not penalised.
Proximity never substitutes for topical relevance (the regional factor is gated by topical fit).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

GEO_SCOPES = ("karlskrona", "blekinge", "sweden", "europe", "international", "online")
GEO_LABELS = {"karlskrona": "Karlskrona", "blekinge": "Blekinge", "sweden": "Sweden", "europe": "Europe",
              "international": "International", "online": "Online"}
IMPLIES = {"karlskrona": ("blekinge", "sweden"), "blekinge": ("sweden",)}

_PATTERNS: dict[str, re.Pattern[str]] = {
    "karlskrona": re.compile(r"\b(karlskrona|lyckeby|gräsvik|rödeby|nättraby)\b", re.I),
    "blekinge": re.compile(r"\b(blekinge\w*|ronneby|karlshamn|sölvesborg|olofström)\b", re.I),
    "sweden": re.compile(r"\b(sweden|swedish|sverige|svensk\w*|nationell\w*|national co-?financing|stockholm|göteborg|gothenburg|"
                         r"malmö|malmo|uppsala|linköping|lund|kalmar|växjö|norrköping|örebro|umeå|luleå|helsingborg|jönköping|halmstad)\b", re.I),
    "europe": re.compile(r"\b(europe\w*|europa\w*|\bEU\b|eu-|horizon europe|eureka|chips ju|eurohpc|cetp|baltic|östersjö\w*|nordic|norden|"
                         r"germany|tyskland|hamburg|berlin|denmark|danmark|copenhagen|köpenhamn|norway|norge|oslo|finland|helsinki|"
                         r"netherlands|rotterdam|amsterdam|france|paris|spain|italy|poland|gdansk|gdańsk|estonia|latvia|lithuania|uk|united kingdom|scotland|london)\b", re.I),
    "international": re.compile(r"\b(international\w*|internationell\w*|global\w*|worldwide|innowwide|countries)\b", re.I),
    "online": re.compile(r"\b(online|webinar\w*|webbinari\w*|digital(?:t)? (?:event|möte|träff)|livesänd\w*|virtual event|teams-möte|zoom)\b", re.I),
}
_HYBRID = re.compile(r"\b(hybrid|på plats och digitalt|on-?site and online)\b", re.I)


def extract_geo(text: str | None) -> dict[str, list[str]]:
    if not text:
        return {}
    found: dict[str, list[str]] = {}
    for scope, pattern in _PATTERNS.items():
        hits = sorted({m.group(0) for m in pattern.finditer(text)})
        if hits:
            found[scope] = hits[:3]
    return found


def expand(scopes: list[str] | set[str]) -> list[str]:
    out = set(scopes)
    for s in list(out):
        out.update(IMPLIES.get(s, ()))
    return [s for s in GEO_SCOPES if s in out]


@dataclass
class OpportunityGeo:
    scopes: list[str]
    basis: str
    inferred: bool
    event_format: str  # physical | online | hybrid | unknown | not_applicable
    format_basis: str


def opportunity_geo(*, organisation: str, category: str, title: str, text: str) -> OpportunityGeo:
    stated = extract_geo(f"{title}\n{text}")
    online_hit = "online" in stated
    hybrid = bool(_HYBRID.search(f"{title} {text}"))
    place_scopes = [s for s in stated if s != "online"]
    if category in ("event", "testing_facility", "business_programme", "ecosystem_news"):
        if hybrid:
            fmt, fbasis = "hybrid", "Source text mentions both on-site and online participation."
        elif online_hit:
            fmt, fbasis = "online", f"Source text says: '{stated['online'][0]}'."
        elif category == "event":
            fmt, fbasis = "unknown", "Format not stated in the collected metadata (in-person is common for this organiser, but not confirmed)."
        else:
            fmt, fbasis = "physical" if category == "testing_facility" else "unknown", (
                "Test environments are physical facilities." if category == "testing_facility" else "Format not stated in collected metadata.")
        # A bare country/region name (e.g. "DigIT Hub Sweden") is usually a programme name, not a venue.
        venue_scopes = [x for x in place_scopes if x not in ("sweden",)] if organisation == "Blue Science Park" else place_scopes
        if venue_scopes:
            place_scopes = venue_scopes
            scopes = expand(place_scopes) + (["online"] if online_hit else [])
            return OpportunityGeo(scopes, "Location stated in source text: " + ", ".join(h for s in place_scopes for h in stated[s][:1]) + ".",
                                  False, fmt, fbasis)
        if organisation == "Blue Science Park":
            scopes = expand(["karlskrona"]) + (["online"] if online_hit else [])
            return OpportunityGeo(scopes, "Inferred: published by Blue Science Park (Karlskrona); venue not stated in collected metadata.",
                                  True, fmt, fbasis)
        return OpportunityGeo(["online"] if online_hit else [], "Location not stated in source.", True, fmt, fbasis)

    # Funding and research programmes: geography describes the programme area, not travel.
    scopes = expand(place_scopes) if place_scopes else []
    basis_parts = []
    if place_scopes:
        basis_parts.append("Source text mentions " + ", ".join(h for s in place_scopes for h in stated[s][:1]) + ".")
    inferred = False
    if organisation == "Vinnova" and "sweden" not in scopes:
        scopes = expand(scopes + ["sweden"])
        basis_parts.append("Inferred: Vinnova is Sweden's national innovation agency.")
        inferred = True
    return OpportunityGeo(scopes, " ".join(basis_parts) or "Programme area not stated in source.", inferred,
                          "not_applicable", "Funding programme (no physical attendance implied).")


@dataclass
class CompanyGeo:
    scopes: list[str]
    label: str
    basis: str
    verified: bool
    claim_ids: list[int] = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"scopes": self.scopes, "label": self.label, "basis": self.basis, "verified": self.verified, "claim_ids": self.claim_ids}


def company_geo(claims, membership_verified: bool) -> CompanyGeo:  # noqa: ANN001
    loc_claims = [c for c in claims if c.field == "location"]
    scopes: set[str] = set()
    ids = []
    for c in loc_claims:
        found = extract_geo(f"{c.label or ''} {c.value}")
        if found:
            scopes.update(s for s in found if s != "online")
            ids.append(c.id)
    scopes_l = expand(scopes)
    if "blekinge" in scopes_l:
        place = "Karlskrona, Blekinge" if "karlskrona" in scopes_l else "Blekinge"
        return CompanyGeo(scopes_l, place, "Location stated on the official website.", True, ids)
    if scopes_l:
        return CompanyGeo(scopes_l, ", ".join(GEO_LABELS[s] for s in scopes_l if s in ("sweden", "europe", "international")),
                          "Location stated on the official website; no Blekinge site stated.", True, ids)
    if membership_verified:
        return CompanyGeo([], "Blekinge ecosystem (location not verified)",
                          "Blue Science Park member; office location not found in collected sources.", False, [])
    return CompanyGeo([], "Location unknown", "No location information collected.", False, [])


# ----------------------------------------------------------------------------------- regional factor
REGIONAL_MAX = 10
PRIORITY_SCALE = {0: 0.25, 1: 0.75, 2: 1.0, 3: 1.25}
PHYSICAL_CATEGORIES = ("event", "testing_facility", "business_programme", "ecosystem_news")


def regional_relevance(company: CompanyGeo, opp_scopes: list[str], opp_inferred: bool, event_format: str, category: str,
                       topical: float, regional_weight: int) -> tuple[float, str, str]:
    """Return (value 0..10, explanation, label). `topical` is the opportunity's topical fit (0..70)."""
    gate = min(1.0, topical / 25.0)
    scale = PRIORITY_SCALE.get(regional_weight, 0.75)
    local_company = "blekinge" in company.scopes
    if event_format == "online":
        base, why, lbl = 6.0, "Online — accessible from anywhere, so location does not reduce relevance.", "Online"
    elif category in PHYSICAL_CATEGORIES:
        if "blekinge" in opp_scopes and local_company:
            base = 9.0 if not opp_inferred else 7.0
            why = ("In Blekinge" + (" (inferred from organiser)" if opp_inferred else "") +
                   " — practical to attend for a company based in " + company.label + ".")
            lbl = "Local · Blekinge"
        elif "blekinge" in opp_scopes:
            base, why, lbl = 4.0, "In Blekinge; the company's own location is not verified.", "Blekinge"
        elif "sweden" in opp_scopes:
            base, why, lbl = 3.0, "Elsewhere in Sweden — attending requires travel.", "Sweden"
        elif "europe" in opp_scopes or "international" in opp_scopes:
            base, why, lbl = 1.5, "Outside Sweden — higher travel cost; still shown when topically relevant.", "Abroad"
        else:
            base, why, lbl = 2.0, "Location not stated in source.", "Location unknown"
    else:  # funding / research programmes
        if "blekinge" in opp_scopes and local_company:
            base, why, lbl = 9.0, "Regional programme in Blekinge, where the company is based.", "Regional programme"
        elif "europe" in opp_scopes or "international" in opp_scopes:
            base, why, lbl = 6.0, "European/international programme — not penalised for being outside the region; check the call's country rules.", "European"
        elif "sweden" in opp_scopes:
            base, why, lbl = 6.0, "National programme — open across Sweden, so the company's location is not a disadvantage.", "National"
        else:
            base, why, lbl = 4.0, "Programme area not stated in source.", "Area not stated"
    value = min(REGIONAL_MAX, base * scale * gate)
    if gate < 1.0:
        why += " (Regional weight reduced because topical relevance is limited — proximity never replaces relevance.)"
    return value, why, lbl


def proximity(company: CompanyGeo, partner: CompanyGeo, rule_value: float, regional_weight: int) -> tuple[float, str]:
    gate = min(1.0, rule_value / 30.0)
    scale = PRIORITY_SCALE.get(regional_weight, 0.75)
    if "blekinge" in company.scopes and "blekinge" in partner.scopes:
        base = 10.0
        why = f"Both have a verified presence in Blekinge ({partner.label}) — easy to meet in person."
    elif partner.scopes and "sweden" in partner.scopes and "sweden" in company.scopes:
        base, why = 4.0, f"Both in Sweden ({partner.label})."
    elif not partner.verified:
        base, why = 0.0, f"{partner.label}: location not verified, so no proximity credit."
    else:
        base, why = 1.0, f"{partner.label}: no shared region."
    return min(10.0, base * scale * gate), why
