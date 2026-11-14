from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Technology(Base, TimestampMixin):
    __tablename__ = "technologies"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    area: Mapped[str] = mapped_column(String(64), nullable=False)  # radar quadrant
    description: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class OpportunityTechnology(Base):
    __tablename__ = "opportunity_technologies"
    __table_args__ = (UniqueConstraint("opportunity_id", "technology_id", name="uq_opp_tech"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    opportunity_id: Mapped[int] = mapped_column(ForeignKey("opportunities.id", ondelete="CASCADE"), nullable=False)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False)
    matched_terms: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)


class CompanyTechnology(Base):
    """Materialised output of the technology relevance service for one company."""

    __tablename__ = "company_technologies"
    __table_args__ = (UniqueConstraint("company_id", "technology_id", name="uq_company_tech"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    technology_id: Mapped[int] = mapped_column(ForeignKey("technologies.id", ondelete="CASCADE"), nullable=False)
    relation: Mapped[str] = mapped_column(String(16), nullable=False)  # core | adjacent | industry | weak
    ring: Mapped[str] = mapped_column(String(16), nullable=False)  # adopt | trial | assess | monitor
    score: Mapped[float] = mapped_column(Float, nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    technology = relationship("Technology")


class CollaborationRecommendation(Base):
    """A *potential* collaboration suggestion. Never represents an existing or agreed partnership."""

    __tablename__ = "collaboration_recommendations"
    __table_args__ = (UniqueConstraint("company_id", "partner_id", name="uq_collab_pair"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    partner_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(Float, nullable=False)
    strength: Mapped[str] = mapped_column(String(16), nullable=False)  # strong | moderate | exploratory
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    partner = relationship("Company", foreign_keys=[partner_id])


class Recommendation(Base, TimestampMixin):
    __tablename__ = "recommendations"
    __table_args__ = (
        UniqueConstraint("company_id", "fingerprint", name="uq_recommendation_fingerprint"),
        Index("ix_recommendations_company_current", "company_id", "is_current"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    fingerprint: Mapped[str] = mapped_column(String(160), nullable=False)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    title: Mapped[str] = mapped_column(String(400), nullable=False)
    priority_tier: Mapped[str] = mapped_column(String(16), nullable=False)  # high | medium | later
    rank_score: Mapped[float] = mapped_column(Float, nullable=False)
    rank_position: Mapped[int] = mapped_column(default=0, nullable=False)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    related_opportunity_id: Mapped[int | None] = mapped_column(ForeignKey("opportunities.id", ondelete="SET NULL"))
    related_company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"))
    related_technology_id: Mapped[int | None] = mapped_column(ForeignKey("technologies.id", ondelete="SET NULL"))
    status: Mapped[str] = mapped_column(String(16), default="open", nullable=False)  # open | saved | dismissed | explored
    status_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    computed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class SavedRecommendation(Base):
    __tablename__ = "saved_recommendations"
    __table_args__ = (UniqueConstraint("recommendation_id", name="uq_saved_recommendation"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    recommendation_id: Mapped[int] = mapped_column(ForeignKey("recommendations.id", ondelete="CASCADE"), nullable=False)
    company_id: Mapped[int] = mapped_column(ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    note: Mapped[str | None] = mapped_column(Text)
    saved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
