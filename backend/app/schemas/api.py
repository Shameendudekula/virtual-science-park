"""API request/response schemas (kept separate from ORM models)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, Literal, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.company import CLAIM_FIELDS
from app.services.intelligence.taxonomy import PRIORITIES

T = TypeVar("T")


def validate_priorities(v: dict[str, int] | None) -> dict[str, int] | None:
    if v is None:
        return v
    for key, weight in v.items():
        if key not in PRIORITIES:
            raise ValueError(f"Unknown priority '{key}'")
        if not isinstance(weight, int) or not 0 <= weight <= 3:
            raise ValueError("Priority weight must be an integer between 0 and 3")
    return v


class Page(BaseModel, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


# ---------------------------------------------------------------------------------------------
class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    title: str
    publisher: str
    url: str
    retrieved_at: datetime
    excerpt: str | None
    evidence_type: str
    provenance: str
    reuse_note: str
    verification_status: str
    verified_at: datetime | None
    source_key: str | None = None


class ClaimOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    field: str
    label: str | None
    value: str
    claim_type: Literal["source_stated", "inferred", "user_provided"]
    status: str
    evidence_id: int | None
    inference_rule: str | None
    inference_explanation: str | None
    derived_from: list[int]
    superseded_by_id: int | None
    reviewed_at: datetime | None
    review_note: str | None
    concepts: list[str] = []
    influences_matching: bool = True


class CompanySummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    slug: str
    name: str
    tagline: str | None
    website: str | None
    profile_level: str
    organisation_type: str
    membership_status: str
    is_demo_company: bool


class CompanyDetail(CompanySummary):
    legal_name: str | None
    membership_evidence: EvidenceOut | None
    overview: str | None
    stats: dict[str, Any]


# ---------------------------------------------------------------------------------------------
class NewClaim(BaseModel):
    field: Literal[CLAIM_FIELDS]  # type: ignore[valid-type]
    value: str = Field(min_length=3, max_length=1000)
    label: str | None = Field(default=None, max_length=200)

    @field_validator("value", "label")
    @classmethod
    def _strip(cls, v: str | None) -> str | None:
        return v.strip() if isinstance(v, str) else v


class ClaimCorrection(BaseModel):
    claim_id: int
    value: str = Field(min_length=3, max_length=1000)
    label: str | None = Field(default=None, max_length=200)
    note: str | None = Field(default=None, max_length=500)


class ProfilePatch(BaseModel):
    add_claims: list[NewClaim] = Field(default_factory=list, max_length=20)
    corrections: list[ClaimCorrection] = Field(default_factory=list, max_length=20)
    priorities: dict[str, int] | None = None

    @field_validator("priorities")
    @classmethod
    def _prios(cls, v: dict[str, int] | None) -> dict[str, int] | None:
        return validate_priorities(v)


class ClaimReview(BaseModel):
    action: Literal["confirm", "reject", "mark_outdated", "restore"]
    note: str | None = Field(default=None, max_length=500)


class PrioritiesUpdate(BaseModel):
    weights: dict[str, int]

    @field_validator("weights")
    @classmethod
    def _w(cls, v: dict[str, int]) -> dict[str, int]:
        return validate_priorities(v)  # type: ignore[return-value]


class RecommendationAction(BaseModel):
    note: str | None = Field(default=None, max_length=500)


class SearchRequest(BaseModel):
    q: str = Field(min_length=2, max_length=300)
    company_id: int | None = None
