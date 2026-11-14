"""Profile review and refinement workflow. Every change is recorded as a ProfileRevision."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import Company, CompanyClaim, CompanyPriority, ProfileRevision


class ReviewNotAllowed(ValueError):
    pass


def _snap(c: CompanyClaim) -> dict:
    return {"field": c.field, "label": c.label, "value": c.value, "claim_type": c.claim_type, "status": c.status}


def _revision(db: Session, company: Company, action: str, claim: CompanyClaim | None, before: dict, after: dict, note: str | None) -> None:
    db.add(ProfileRevision(company_id=company.id, claim_id=claim.id if claim else None, action=action, before=before, after=after,
                           note=note, created_at=utcnow()))


def add_claim(db: Session, company: Company, field: str, value: str, label: str | None) -> CompanyClaim:
    existing = db.scalar(select(CompanyClaim).where(CompanyClaim.company_id == company.id, CompanyClaim.field == field,
                                                    CompanyClaim.value == value, CompanyClaim.claim_type == "user_provided"))
    if existing:
        if existing.status in ("rejected", "outdated"):
            existing.status = "active"
        return existing
    claim = CompanyClaim(company_id=company.id, field=field, value=value, label=label or value[:80], claim_type="user_provided", status="active")
    db.add(claim)
    db.flush()
    _revision(db, company, "add", claim, {}, _snap(claim), None)
    return claim


def correct_claim(db: Session, company: Company, claim: CompanyClaim, value: str, label: str | None, note: str | None) -> CompanyClaim:
    """Source-stated and inferred claims are never edited in place: they are superseded by a user-provided correction."""
    before = _snap(claim)
    if claim.claim_type == "user_provided":
        claim.value = value
        claim.label = label or claim.label
        _revision(db, company, "edit", claim, before, _snap(claim), note)
        return claim
    correction = CompanyClaim(company_id=company.id, field=claim.field, value=value, label=label or claim.label,
                              claim_type="user_provided", status="active", review_note=note)
    db.add(correction)
    db.flush()
    claim.status = "corrected"
    claim.superseded_by_id = correction.id
    claim.reviewed_at = utcnow()
    claim.review_note = note
    _revision(db, company, "correct", claim, before, {**_snap(correction), "supersedes": claim.id}, note)
    return correction


ALLOWED = {
    "source_stated": {"confirm", "mark_outdated", "restore"},
    "inferred": {"confirm", "reject", "mark_outdated", "restore"},
    "user_provided": {"confirm", "reject", "mark_outdated", "restore"},
}
NEW_STATUS = {"confirm": "confirmed", "reject": "rejected", "mark_outdated": "outdated", "restore": "active"}


def review_claim(db: Session, company: Company, claim: CompanyClaim, action: str, note: str | None) -> CompanyClaim:
    if action not in ALLOWED[claim.claim_type]:
        raise ReviewNotAllowed(
            "Source-stated facts cannot be rejected; mark them as outdated or add a correction instead."
            if claim.claim_type == "source_stated" else f"Action '{action}' is not allowed for this claim."
        )
    if claim.status == "corrected" and action != "restore":
        raise ReviewNotAllowed("This claim has been superseded by a correction; restore it first.")
    before = _snap(claim)
    claim.status = NEW_STATUS[action]
    claim.reviewed_at = utcnow()
    claim.review_note = note
    if action == "restore":
        claim.superseded_by_id = None
    _revision(db, company, action, claim, before, _snap(claim), note)
    return claim


def set_priorities(db: Session, company: Company, weights: dict[str, int]) -> dict[str, int]:
    current = {p.key: p for p in company.priorities}
    before = {k: p.weight for k, p in current.items()}
    for key, weight in weights.items():
        if key in current:
            current[key].weight = weight
        else:
            company.priorities.append(CompanyPriority(key=key, weight=weight))
    db.flush()
    after = {p.key: p.weight for p in company.priorities}
    _revision(db, company, "priorities", None, before, after, None)
    return after
