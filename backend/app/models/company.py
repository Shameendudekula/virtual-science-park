from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, CheckConstraint, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint, event, inspect
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.db.base import Base, TimestampMixin

CLAIM_FIELDS = (
    "overview",
    "product",
    "service",
    "technology",
    "capability",
    "industry",
    "research_interest",
    "business_focus",
    "project",
    "documented_collaboration",
    "location",
    "interest",
)
CLAIM_TYPES = ("source_stated", "inferred", "user_provided")
CLAIM_STATUSES = ("active", "confirmed", "rejected", "outdated", "corrected")


class Company(Base, TimestampMixin):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False, index=True)
    legal_name: Mapped[str | None] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))
    tagline: Mapped[str | None] = mapped_column(String(300))
    # full = demo-grade profile; partial = lightweight evidence-backed profile; directory = membership listing only
    profile_level: Mapped[str] = mapped_column(String(16), default="directory", nullable=False)
    organisation_type: Mapped[str] = mapped_column(String(32), default="company", nullable=False)  # company | university | public_agency
    membership_status: Mapped[str] = mapped_column(String(16), default="unverified", nullable=False)  # verified | unverified
    membership_evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="SET NULL"))
    bsp_member_id: Mapped[int | None] = mapped_column(Integer, unique=True)
    is_demo_company: Mapped[bool] = mapped_column(default=False, nullable=False)

    claims: Mapped[list[CompanyClaim]] = relationship(back_populates="company", cascade="all, delete-orphan")
    priorities: Mapped[list[CompanyPriority]] = relationship(back_populates="company", cascade="all, delete-orphan")
    membership_evidence = relationship("Evidence", foreign_keys=[membership_evidence_id])


class CompanyClaim(Base, TimestampMixin):
    """One statement about a company. The type distinguishes source facts, rule inferences and user input."""

    __tablename__ = "company_claims"
    __table_args__ = (
        CheckConstraint(f"claim_type IN {CLAIM_TYPES}", name="claim_type_valid"),
        CheckConstraint(f"status IN {CLAIM_STATUSES}", name="status_valid"),
        # A source-stated claim must cite evidence.
        CheckConstraint("claim_type <> 'source_stated' OR evidence_id IS NOT NULL", name="stated_requires_evidence"),
        UniqueConstraint("company_id", "field", "value", "claim_type", name="uq_claim_company_field_value_type"),
        Index("ix_company_claims_company_field", "company_id", "field"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    field: Mapped[str] = mapped_column(String(32), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[str | None] = mapped_column(String(200))  # short display label
    claim_type: Mapped[str] = mapped_column(String(16), nullable=False)
    status: Mapped[str] = mapped_column(String(16), default="active", nullable=False)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="SET NULL"))
    inference_rule: Mapped[str | None] = mapped_column(String(64))
    inference_explanation: Mapped[str | None] = mapped_column(Text)
    derived_from: Mapped[list[int]] = mapped_column(JSON, default=list, nullable=False)
    concepts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    superseded_by_id: Mapped[int | None] = mapped_column(ForeignKey("company_claims.id", ondelete="SET NULL"))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    review_note: Mapped[str | None] = mapped_column(Text)

    company: Mapped[Company] = relationship(back_populates="claims")
    evidence = relationship("Evidence")

    @property
    def is_effective(self) -> bool:
        """Whether the claim currently influences matching."""
        return self.status in ("active", "confirmed")


class CompanyPriority(Base, TimestampMixin):
    """Company-specific business priorities set by a company representative. Isolated per company."""

    __tablename__ = "company_priorities"
    __table_args__ = (
        UniqueConstraint("company_id", "key", name="uq_priority_company_key"),
        CheckConstraint("weight >= 0 AND weight <= 3", name="weight_range"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    key: Mapped[str] = mapped_column(String(48), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, default=1, nullable=False)  # 0 off, 1 normal, 2 important, 3 top

    company: Mapped[Company] = relationship(back_populates="priorities")


class ProfileRevision(Base):
    """Audit trail for every profile edit, review decision and priority change."""

    __tablename__ = "profile_revisions"
    __table_args__ = (Index("ix_profile_revisions_company_created", "company_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    claim_id: Mapped[int | None] = mapped_column(ForeignKey("company_claims.id", ondelete="SET NULL"))
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    before: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    after: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class CompanyAccount(Base, TimestampMixin):
    """One login per company workspace (hackathon scope: no multi-user roles)."""

    __tablename__ = "company_accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), unique=True, nullable=False)
    username: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(300), nullable=False)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class SearchHistory(Base):
    """Company-specific question history. Visible only to that company's workspace."""

    __tablename__ = "search_history"
    __table_args__ = (Index("ix_search_history_company_created", "company_id", "created_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    query: Mapped[str] = mapped_column(String(300), nullable=False)
    intent: Mapped[str] = mapped_column(String(32), nullable=False)
    result_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SourceFactImmutableError(RuntimeError):
    """Raised when code tries to change the content of a source-stated claim."""


IMMUTABLE_STATED_FIELDS = ("value", "field", "evidence_id", "claim_type", "label")


@event.listens_for(Session, "before_flush")
def _protect_source_facts(session: Session, _ctx, _instances) -> None:  # noqa: ANN001
    """Source-stated facts can change status (e.g. outdated/corrected) but never their content or type."""
    for obj in session.dirty:
        if isinstance(obj, CompanyClaim):
            state = inspect(obj)
            ct_hist = state.attrs.claim_type.history
            was_stated = (ct_hist.deleted and ct_hist.deleted[0] == "source_stated") or (not ct_hist.deleted and obj.claim_type == "source_stated")
            if not was_stated:
                continue
            for attr in IMMUTABLE_STATED_FIELDS:
                if state.attrs[attr].history.has_changes():
                    raise SourceFactImmutableError(
                        f"Claim {obj.id} is source-stated; its '{attr}' cannot be changed. Add a correction instead."
                    )
