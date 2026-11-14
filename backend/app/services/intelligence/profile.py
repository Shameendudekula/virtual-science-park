"""Company profile model used by every matching service: effective claims -> weighted concepts."""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Company, CompanyClaim, CompanyPriority
from app.services.intelligence.concepts import extract
from app.services.intelligence.taxonomy import ALL_CONCEPTS, DEFAULT_PRIORITY_WEIGHT, PRIORITIES

# Which concept kinds a claim field may contribute. An *interest* is not a *capability*.
FIELD_CONCEPT_KINDS: dict[str, tuple[str, ...]] = {
    "overview": ("technology", "domain", "capability"),
    "product": ("technology", "domain", "capability"),
    "service": ("technology", "domain", "capability"),
    "technology": ("technology", "domain", "capability"),
    "capability": ("technology", "domain", "capability"),
    "project": ("technology", "domain", "capability"),
    "documented_collaboration": ("technology", "domain"),
    "industry": ("technology", "domain"),
    "business_focus": ("technology", "domain", "capability"),
    "research_interest": ("technology", "domain"),
    "interest": ("technology", "domain"),
    "location": (),
}
CAPABILITY_FIELDS = {"product", "service", "technology", "capability", "project", "overview", "business_focus"}
INTEREST_FIELDS = {"interest", "research_interest"}


def claim_strength_public(claim: CompanyClaim, user_claim_ids: set[int]) -> float:
    """Strength as seen by OTHER companies: public source facts and rule inferences only.

    A company's private workspace actions (user-provided claims, review decisions, inferences derived from
    its own private input) are never visible to, nor influence results for, another company.
    """
    if claim.claim_type == "source_stated":
        return 1.0
    if claim.claim_type == "inferred" and not (set(claim.derived_from or []) & user_claim_ids):
        return 0.5
    return 0.0


def claim_strength(claim: CompanyClaim) -> float:
    """How much a claim is trusted for matching. Rejected/outdated/corrected claims have no influence."""
    if claim.status not in ("active", "confirmed"):
        return 0.0
    if claim.claim_type == "source_stated":
        return 1.0
    if claim.claim_type == "user_provided":
        return 0.9
    # inferred
    return 0.9 if claim.status == "confirmed" else 0.5


def claim_concepts(claim: CompanyClaim) -> dict[str, tuple[list[str], bool]]:
    allowed = FIELD_CONCEPT_KINDS.get(claim.field, ("technology", "domain"))
    text = f"{claim.label or ''}. {claim.value}"
    return {
        k: (m.terms, m.direct)
        for k, m in extract(text).items()
        if ALL_CONCEPTS[k].kind in allowed
    }


@dataclass
class ConceptSupport:
    key: str
    strength: float  # 0..1, max over supporting claims
    claims: list[CompanyClaim] = field(default_factory=list)
    via_interest_only: bool = True


@dataclass
class CompanyProfileModel:
    company: Company
    claims: list[CompanyClaim]
    concepts: dict[str, ConceptSupport]
    priorities: dict[str, int]
    public: bool = False
    geo: object = None  # geography.CompanyGeo

    def strength(self, key: str) -> float:
        c = self.concepts.get(key)
        return c.strength if c else 0.0

    def support(self, key: str) -> ConceptSupport | None:
        return self.concepts.get(key)

    def has(self, key: str, min_strength: float = 0.01) -> bool:
        return self.strength(key) >= min_strength

    def strength_of(self, claim: CompanyClaim) -> float:
        if self.public:
            user_ids = {c.id for c in self.claims if c.claim_type == "user_provided"}
            return claim_strength_public(claim, user_ids)
        return claim_strength(claim)

    @property
    def effective_claims(self) -> list[CompanyClaim]:
        return [c for c in self.claims if self.strength_of(c) > 0]

    def claim_labels(self, key: str, limit: int = 3) -> list[str]:
        s = self.concepts.get(key)
        return [c.label or c.value[:80] for c in (s.claims if s else [])][:limit]


def load_company(db: Session, company_id: int) -> Company | None:
    return db.scalar(
        select(Company).options(selectinload(Company.claims), selectinload(Company.priorities)).where(Company.id == company_id)
    )


def priority_weights(company: Company) -> dict[str, int]:
    weights = {k: DEFAULT_PRIORITY_WEIGHT for k in PRIORITIES}
    for p in company.priorities:
        if p.key in weights:
            weights[p.key] = p.weight
    return weights


def build_profile(company: Company, *, public: bool = False) -> CompanyProfileModel:
    from app.services.intelligence.geography import company_geo

    concepts: dict[str, ConceptSupport] = {}
    user_ids = {c.id for c in company.claims if c.claim_type == "user_provided"}
    for claim in company.claims:
        base = claim_strength_public(claim, user_ids) if public else claim_strength(claim)
        if base <= 0:
            continue
        for key, (_terms, direct) in claim_concepts(claim).items():
            strength = base * (1.0 if direct else 0.7)
            support = concepts.setdefault(key, ConceptSupport(key, 0.0))
            support.strength = max(support.strength, strength)
            support.claims.append(claim)
            if claim.field not in INTEREST_FIELDS:
                support.via_interest_only = False
    for support in concepts.values():
        support.claims.sort(key=lambda c: (-(claim_strength_public(c, user_ids) if public else claim_strength(c)), c.id or 0))
    visible = [c for c in company.claims if (claim_strength_public(c, user_ids) if public else claim_strength(c)) > 0]
    priorities = {k: DEFAULT_PRIORITY_WEIGHT for k in PRIORITIES} if public else priority_weights(company)
    geo = company_geo(visible, company.membership_status == "verified")
    return CompanyProfileModel(company=company, claims=list(company.claims), concepts=concepts, priorities=priorities,
                               public=public, geo=geo)


def get_profile(db: Session, company_id: int) -> CompanyProfileModel | None:
    company = load_company(db, company_id)
    return build_profile(company) if company else None


def ensure_priorities(db: Session, company: Company) -> None:
    existing = {p.key for p in company.priorities}
    for key in PRIORITIES:
        if key not in existing:
            company.priorities.append(CompanyPriority(key=key, weight=DEFAULT_PRIORITY_WEIGHT))
    db.flush()
