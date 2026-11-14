"""Idempotent persistence helpers shared by collectors."""
from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Evidence, Opportunity, Source
from app.services.collectors.base import UpsertStats
from app.services.collectors.text import sha256
from app.services.matching.tagging import tag_opportunity

HASHED_FIELDS = (
    "title", "title_original", "description", "purpose_text", "eligibility_text", "funding_text", "category", "organisation",
    "programme", "source_url", "apply_url", "published_at", "opens_at", "deadline_at", "deadline_status", "rolling_assessment",
    "decision_expected_at", "quality_flags", "language",
)


def _canonical(record: dict[str, Any]) -> str:
    def conv(v: Any) -> Any:
        return v.isoformat() if isinstance(v, datetime) else v

    return json.dumps({k: conv(record.get(k)) for k in HASHED_FIELDS}, sort_keys=True, ensure_ascii=False)


def upsert_evidence(
    db: Session, *, source: Source, url: str, title: str, publisher: str, excerpt: str | None, evidence_type: str,
    provenance: str, retrieved_at: datetime, reuse_note: str = "",
) -> Evidence:
    excerpt_hash = sha256(excerpt or "")
    existing = db.scalar(select(Evidence).where(Evidence.url == url, Evidence.excerpt_hash == excerpt_hash))
    if existing:
        if retrieved_at >= existing.retrieved_at:
            existing.retrieved_at = retrieved_at
            existing.title = title
            if provenance == "live" or existing.provenance != "live":
                existing.provenance = provenance
        return existing
    ev = Evidence(
        source_id=source.id, url=url, title=title[:500], publisher=publisher, excerpt=excerpt, excerpt_hash=excerpt_hash,
        evidence_type=evidence_type, provenance=provenance, retrieved_at=retrieved_at, reuse_note=reuse_note,
    )
    db.add(ev)
    db.flush()
    return ev


def upsert_opportunity(
    db: Session, source: Source, record: dict[str, Any], *, mode: str, retrieved_at: datetime, stats: UpsertStats,
    evidence_excerpt: str | None, reuse_note: str,
) -> Opportunity | None:
    content_hash = sha256(_canonical(record))
    existing = db.scalar(
        select(Opportunity).where(Opportunity.source_id == source.id, Opportunity.external_id == record["external_id"])
    )
    provenance = "live" if mode == "live" else "snapshot"
    if existing is not None:
        # Never let an older snapshot overwrite newer collected data.
        if existing.retrieved_at and retrieved_at < existing.retrieved_at:
            stats.unchanged += 1
            return existing
        if existing.content_hash == content_hash:
            existing.retrieved_at = retrieved_at
            if provenance == "live":
                existing.provenance = "live"
            stats.unchanged += 1
            return existing
        target = existing
        stats.updated += 1
    else:
        target = Opportunity(source_id=source.id, external_id=record["external_id"])
        db.add(target)
        stats.created += 1

    for key in HASHED_FIELDS:
        setattr(target, key, record.get(key))
    target.provenance = provenance
    target.retrieved_at = retrieved_at
    target.content_hash = content_hash
    target.is_active = True
    db.flush()
    ev = upsert_evidence(
        db, source=source, url=target.source_url, title=target.title, publisher=record["organisation"],
        excerpt=evidence_excerpt, evidence_type="public_api_record" if source.source_type == "public_api" and evidence_excerpt else "news_metadata",
        provenance=provenance, retrieved_at=retrieved_at, reuse_note=reuse_note,
    )
    target.evidence_id = ev.id
    tag_opportunity(db, target)
    return target
