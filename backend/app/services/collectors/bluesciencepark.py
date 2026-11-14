"""Blue Science Park WordPress REST collectors. Minimum metadata only (id, title, date, link)."""
from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Company, Source
from app.services.collectors.base import Collector, SourceUnavailable, UpsertStats
from app.services.collectors.store import upsert_evidence, upsert_opportunity
from app.services.collectors.text import clean_field

WP = "https://www.bluesciencepark.se/wp-json/wp/v2"
FIELDS = "id,date,modified,link,title,slug"
METADATA_NOTE = "Metadata only (title, date, link). Content is not stored, reused or sent to an external LLM; open the link to read it."

_POST_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("ecosystem_news", re.compile(r"ny medlem|new member|blir ny medlem|välkommen .* vd|ny vd", re.I)),
    ("testing_facility", re.compile(r"\btesta\b|testmiljö|testbädd|test ?bed|\blab\b|laborator", re.I)),
    ("business_programme", re.compile(r"\bhub\b|program|accelerat|inkubator|incubator|stöd|support|projekt|project", re.I)),
)


def classify_post(title: str) -> str:
    for category, pattern in _POST_RULES:
        if pattern.search(title):
            return category
    return "ecosystem_news"


def _parse_wp_date(value: Any) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=UTC)


def _valid_link(link: Any) -> str | None:
    link = str(link or "")
    if re.match(r"^https://(www\.)?bluesciencepark\.se/", link):
        return link[:1000]
    return None


def _fetch_pages(client, endpoint: str, pages: int, per_page: int) -> list[dict]:  # noqa: ANN001
    items: list[dict] = []
    for page in range(1, pages + 1):
        try:
            result = client.get(endpoint, params={"per_page": per_page, "page": page, "_fields": FIELDS, "orderby": "date", "order": "desc"})
        except Exception as exc:  # noqa: BLE001
            if page == 1:
                raise SourceUnavailable(f"Blue Science Park API unavailable: {type(exc).__name__}") from exc
            break  # later pages missing is acceptable (end of list)
        data = result.json()
        if not isinstance(data, list):
            raise SourceUnavailable("Unexpected payload from Blue Science Park API")
        items.extend(d for d in data if isinstance(d, dict))
        if len(data) < per_page:
            break
    return items


class _BspOpportunityCollector(Collector):
    endpoint: str
    pages: int = 2
    per_page: int = 50

    def fetch_live(self, db: Session) -> list[dict]:
        with self.client() as client:
            return _fetch_pages(client, f"{WP}/{self.endpoint}", self.pages, self.per_page)

    def category_for(self, title: str) -> str:
        raise NotImplementedError

    def ingest(self, db: Session, source: Source, payload: Any, mode: str, retrieved_at: datetime, stats: UpsertStats) -> None:
        if not isinstance(payload, list):
            raise SourceUnavailable("Blue Science Park payload is not a list")
        seen: set[str] = set()
        for raw in payload:
            stats.fetched += 1
            ext = str(raw.get("id") or "")
            title = clean_field((raw.get("title") or {}).get("rendered") if isinstance(raw.get("title"), dict) else raw.get("title"), 500)
            link = _valid_link(raw.get("link"))
            if not ext.isdigit() or not title or not link:
                stats.reject("missing_required_metadata")
                continue
            if ext in seen:
                stats.reject("duplicate_in_payload")
                continue
            seen.add(ext)
            category = self.category_for(title)
            flags = ["metadata_only"]
            if category == "event":
                flags.append("event_date_not_in_metadata")
            record = {
                "external_id": ext, "title": title, "title_original": None, "description": None, "purpose_text": None,
                "eligibility_text": None, "funding_text": None, "category": category, "organisation": "Blue Science Park",
                "programme": None, "source_url": link, "apply_url": None, "language": "sv",
                "published_at": _parse_wp_date(raw.get("date")), "opens_at": None, "deadline_at": None,
                "deadline_status": "not_stated", "rolling_assessment": False, "decision_expected_at": None, "quality_flags": flags,
            }
            upsert_opportunity(db, source, record, mode=mode, retrieved_at=retrieved_at, stats=stats, evidence_excerpt=None, reuse_note=METADATA_NOTE)


class BspNewsCollector(_BspOpportunityCollector):
    key = "bsp_news"
    endpoint = "posts"

    def category_for(self, title: str) -> str:
        return classify_post(title)


class BspEventsCollector(_BspOpportunityCollector):
    key = "bsp_events"
    endpoint = "event"
    pages = 1

    def category_for(self, title: str) -> str:
        return "event"


class BspMembersCollector(Collector):
    """Verifies membership; creates directory-level entries for members without a VSP profile."""

    key = "bsp_members"

    def fetch_live(self, db: Session) -> list[dict]:
        with self.client() as client:
            return _fetch_pages(client, f"{WP}/medlem", pages=3, per_page=100)

    def ingest(self, db: Session, source: Source, payload: Any, mode: str, retrieved_at: datetime, stats: UpsertStats) -> None:
        if not isinstance(payload, list):
            raise SourceUnavailable("Blue Science Park member payload is not a list")
        provenance = "live" if mode == "live" else "snapshot"
        for raw in payload:
            stats.fetched += 1
            member_id = raw.get("id")
            name = clean_field((raw.get("title") or {}).get("rendered") if isinstance(raw.get("title"), dict) else None, 200)
            link = _valid_link(raw.get("link"))
            slug = clean_field(raw.get("slug"), 100)
            if not isinstance(member_id, int) or not name or not link or not slug:
                stats.reject("missing_required_metadata")
                continue
            ev = upsert_evidence(
                db, source=source, url=link, title=f"{name} — Blue Science Park member directory", publisher="Blue Science Park",
                excerpt=None, evidence_type="member_directory", provenance=provenance, retrieved_at=retrieved_at, reuse_note=METADATA_NOTE,
            )
            company = db.scalar(select(Company).where(Company.bsp_member_id == member_id))
            if company is None:
                company = db.scalar(select(Company).where(Company.slug == f"bsp-{slug}"))
            if company is None:
                company = Company(
                    slug=f"bsp-{slug}", name=name, profile_level="directory", organisation_type="company",
                    membership_status="verified", bsp_member_id=member_id, membership_evidence_id=ev.id,
                )
                db.add(company)
                stats.created += 1
            elif company.membership_status != "verified" or company.membership_evidence_id != ev.id:
                company.membership_status = "verified"
                company.membership_evidence_id = ev.id
                company.bsp_member_id = member_id
                stats.updated += 1
            else:
                stats.unchanged += 1
            db.flush()
