from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin

OPPORTUNITY_CATEGORIES = (
    "funding_call",
    "research_funding",
    "innovation_programme",
    "business_programme",
    "event",
    "testing_facility",
    "research_collaboration",
    "ecosystem_news",
)


class Opportunity(Base, TimestampMixin):
    __tablename__ = "opportunities"
    __table_args__ = (
        UniqueConstraint("source_id", "external_id", name="uq_opportunity_source_external"),
        Index("ix_opportunities_deadline", "deadline_at"),
        Index("ix_opportunities_category", "category"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
    external_id: Mapped[str] = mapped_column(String(120), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    title_original: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str | None] = mapped_column(Text)
    purpose_text: Mapped[str | None] = mapped_column(Text)
    # Verbatim "who can apply" text from the source. VSP never decides eligibility itself.
    eligibility_text: Mapped[str | None] = mapped_column(Text)
    funding_text: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    organisation: Mapped[str] = mapped_column(String(200), nullable=False)
    programme: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    apply_url: Mapped[str | None] = mapped_column(String(1000))
    language: Mapped[str] = mapped_column(String(8), default="en", nullable=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # stated | not_stated | placeholder_rejected
    deadline_status: Mapped[str] = mapped_column(String(24), default="not_stated", nullable=False)
    rolling_assessment: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    decision_expected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    provenance: Mapped[str] = mapped_column(String(16), nullable=False)  # live | snapshot | demo
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    quality_flags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    concepts: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)  # concept_key -> matched terms
    # Regional intelligence (see services/intelligence/geography.py)
    geo_scopes: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    geo_basis: Mapped[str | None] = mapped_column(Text)
    geo_inferred: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    event_format: Mapped[str] = mapped_column(String(16), default="not_applicable", nullable=False)
    format_basis: Mapped[str | None] = mapped_column(Text)
    evidence_id: Mapped[int | None] = mapped_column(ForeignKey("evidence.id", ondelete="SET NULL"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    source = relationship("Source")
    evidence = relationship("Evidence")
