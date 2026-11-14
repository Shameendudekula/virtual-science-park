"""Evidence integrity collector: re-fetches official company pages and checks each excerpt is still present."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import Evidence, Source
from app.services.collectors.base import Collector, SourceUnavailable, UpsertStats, get_source
from app.services.collectors.text import contains_excerpt, html_to_text


class EvidenceVerifierCollector(Collector):
    key = "company_websites"

    def fetch_live(self, db: Session) -> dict[str, Any]:
        source = get_source(db, self.key)
        rows = db.scalars(select(Evidence).where(Evidence.source_id == source.id, Evidence.excerpt.is_not(None))).all()
        urls = sorted({r.url for r in rows})
        pages: dict[str, str | None] = {}
        errors = 0
        with self.client() as client:
            for url in urls:
                try:
                    pages[url] = html_to_text(client.get(url).text)
                except Exception:  # noqa: BLE001 - recorded per page
                    pages[url] = None
                    errors += 1
        if urls and errors == len(urls):
            raise SourceUnavailable("None of the official company pages could be fetched")
        return {"pages": pages}

    def load_snapshot(self) -> tuple[Any, datetime]:
        # Seed evidence is verified when collected; there is no separate snapshot to replay.
        return {"pages": {}}, utcnow()

    def ingest(self, db: Session, source: Source, payload: Any, mode: str, retrieved_at: datetime, stats: UpsertStats) -> None:
        pages: dict[str, str | None] = payload.get("pages", {})
        by_url: dict[str, list[Evidence]] = defaultdict(list)
        for ev in db.scalars(select(Evidence).where(Evidence.source_id == source.id, Evidence.excerpt.is_not(None))):
            by_url[ev.url].append(ev)
        for url, text in pages.items():
            stats.fetched += 1
            for ev in by_url.get(url, []):
                if text is None:
                    new_status = "fetch_failed"
                elif contains_excerpt(text, ev.excerpt or ""):
                    new_status = "verified"
                else:
                    new_status = "not_found"
                if new_status != ev.verification_status:
                    stats.updated += 1
                else:
                    stats.unchanged += 1
                ev.verification_status = new_status
                if new_status == "verified":
                    ev.verified_at = retrieved_at
                    ev.retrieved_at = retrieved_at
                    ev.provenance = "live"
