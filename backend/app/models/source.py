from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Source(Base, TimestampMixin):
    """Registry of data sources. New sources are added here (and as a collector adapter) without app rewrites."""

    __tablename__ = "sources"

    id: Mapped[int] = mapped_column(primary_key=True)
    key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    publisher: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)  # public_api | website | directory | curated | user
    base_url: Mapped[str | None] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    license_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    allowed_hosts: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    collectable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # Whether content from this source may be sent to an external LLM. False unless permission is confirmed.
    llm_allowed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    disabled_reason: Mapped[str | None] = mapped_column(Text)

    health: Mapped[SourceHealth | None] = relationship(back_populates="source", uselist=False, cascade="all, delete-orphan")


class SourceHealth(Base):
    __tablename__ = "source_health"

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="never_run", nullable=False)  # healthy | degraded | failing | never_run | snapshot_only
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_success_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(Text)
    consecutive_failures: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    record_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    data_mode: Mapped[str] = mapped_column(String(16), default="snapshot", nullable=False)  # live | snapshot | demo

    source: Mapped[Source] = relationship(back_populates="health")


class CollectionRun(Base):
    __tablename__ = "collection_runs"
    __table_args__ = (Index("ix_collection_runs_source_started", "source_id", "started_at"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)  # live | snapshot
    trigger: Mapped[str] = mapped_column(String(32), default="manual", nullable=False)  # manual | seed | startup
    status: Mapped[str] = mapped_column(String(16), default="running", nullable=False)  # running | success | partial | failed
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_fetched: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_unchanged: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    records_rejected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    rejection_reasons: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text)


class Evidence(Base, TimestampMixin):
    """A citable piece of evidence: where a fact came from, when it was retrieved, and what it says."""

    __tablename__ = "evidence"
    __table_args__ = (
        UniqueConstraint("url", "excerpt_hash", name="uq_evidence_url_excerpt"),
        Index("ix_evidence_source", "source_id"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("sources.id", ondelete="RESTRICT"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    publisher: Mapped[str] = mapped_column(String(200), nullable=False)
    url: Mapped[str] = mapped_column(String(1000), nullable=False)
    retrieved_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    excerpt: Mapped[str | None] = mapped_column(Text)
    excerpt_hash: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    # official_website | public_api_record | member_directory | news_metadata | user_input
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)
    provenance: Mapped[str] = mapped_column(String(16), nullable=False)  # live | snapshot | demo | user
    reuse_note: Mapped[str] = mapped_column(Text, default="", nullable=False)
    # Evidence integrity check: was the excerpt still found at the URL the last time we looked?
    verification_status: Mapped[str] = mapped_column(String(24), default="not_checked", nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    source: Mapped[Source] = relationship()
