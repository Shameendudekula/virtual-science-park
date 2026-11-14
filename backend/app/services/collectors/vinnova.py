"""Vinnova open-data collector (calls + application rounds)."""
from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.core.clock import today
from app.models import Source
from app.security.url_guard import UrlRejected
from app.services.collectors.base import Collector, SourceUnavailable, UpsertStats
from app.services.collectors.store import upsert_opportunity
from app.services.collectors.text import clean_field

API = "https://data.vinnova.se/api"
STOCKHOLM = ZoneInfo("Europe/Stockholm")
PLACEHOLDER_TITLES = {"x", "xx", "xxx", "na", "n/a", ".", "-", "--", "---", "nnn", "tbd", ""}
LOOKBACK_DAYS = 400
RECENT_CLOSE_GRACE_DAYS = 120  # recently closed rounds are kept as context (shown as Closed, never recommended)
REUSE_NOTE = "Vinnova open data. Text shown with attribution and a link to the official record. Contact persons are not collected."

_CATEGORY_RULES: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("testing_facility", re.compile(r"\btesting\b|\btest ?beds?\b|testbädd|pilot lines?|testmiljö", re.I)),
    ("research_collaboration", re.compile(r"eureka|chips ju|eurohpc|\bmsca\b|horizon|european partnership|european collaborat|international collaborat|internationell|co-?fund|era-?net|partnership", re.I)),
    ("innovation_programme", re.compile(r"challenge", re.I)),
    ("business_programme", re.compile(r"start-?ups?|scale-?up|incubat|accelerat|travel grant|skills supply|kompetensförsörjning|innovation vouchers?", re.I)),
    ("research_funding", re.compile(r"competence cent|kompetenscent|research and innovation project|forsknings- och innovationsprojekt|research project", re.I)),
    ("innovation_programme", re.compile(r"strategic innovation|\bSIP\b|strategic project|strategiska|innovation platform|programme|program\b", re.I)),
)


def classify(title: str | None, programme: str | None = None, *body: str | None) -> str:
    """Classify by title first, then programme name, then body text. 'Testing' is only trusted in title/programme."""
    for i, text in enumerate((title, programme, " ".join(b for b in body if b))):
        if not text:
            continue
        for category, pattern in _CATEGORY_RULES:
            if category == "testing_facility" and i == 2:
                continue
            if pattern.search(text):
                return category
    return "funding_call"


def _is_placeholder(title: str | None) -> bool:
    return (title or "").strip().lower() in PLACEHOLDER_TITLES


def parse_local_datetime(value: Any) -> tuple[datetime | None, str]:
    """Parse a Vinnova local timestamp. Returns (value, status) where status is stated|not_stated|placeholder_rejected."""
    if not value:
        return None, "not_stated"
    try:
        dt = datetime.fromisoformat(str(value))
    except ValueError:
        return None, "not_stated"
    # Vinnova uses 1900-01-01 style placeholders; far-future values are equally not real deadlines.
    if dt.year < 2000 or dt.year > today().year + 8:
        return None, "placeholder_rejected"
    return dt.replace(tzinfo=STOCKHOLM), "stated"


def _web_text(record: dict, text_id: int) -> str | None:
    for item in record.get("WebTextLista") or []:
        if item.get("TextID") == text_id:
            return clean_field(item.get("TextEn")) or clean_field(item.get("TextSv"))
    return None


def _apply_link(record: dict) -> str | None:
    for link in record.get("LankLista") or []:
        url = str(link.get("URL") or "")
        if url.startswith("https://") and ("vinnova.se" in url):
            return url[:1000]
    return None


def parse_round(record: dict, calls: dict[str, dict], stats: UpsertStats) -> dict | None:
    dnr = clean_field(record.get("Diarienummer"), 40)
    if not dnr or not re.fullmatch(r"\d{4}-\d{5}", dnr):
        stats.reject("missing_or_invalid_id")
        return None
    if record.get("Publik") != 1:
        stats.reject("not_public")
        return None
    title_en = clean_field(record.get("TitelEngelska"), 500)
    title_sv = clean_field(record.get("Titel"), 500)
    flags: list[str] = []
    if _is_placeholder(title_en):
        if _is_placeholder(title_sv):
            stats.reject("placeholder_title")
            return None
        title, language = title_sv, "sv"
        flags.append("english_title_missing")
    else:
        title, language = title_en, "en"

    deadline, deadline_status = parse_local_datetime(record.get("Stangningsdatum"))
    opens, _ = parse_local_datetime(record.get("Oppningsdatum"))
    decision, _ = parse_local_datetime(record.get("UppskattatBeslutsdatum"))
    if deadline_status == "placeholder_rejected":
        flags.append("deadline_placeholder_rejected")
    if deadline is not None and deadline.date() < today() - timedelta(days=RECENT_CLOSE_GRACE_DAYS):
        stats.reject("closed_before_collection")
        return None

    description = clean_field(record.get("BeskrivningEngelska")) if language == "en" else None
    description = description if description and not _is_placeholder(description) else clean_field(record.get("Beskrivning"))
    purpose = _web_text(record, 1)
    eligibility = _web_text(record, 2)
    funding = _web_text(record, 3)
    if not eligibility:
        flags.append("no_eligibility_text")
    apply_url = _apply_link(record)
    if not apply_url:
        flags.append("no_apply_link")

    call = calls.get(str(record.get("DiarienummerUtlysning") or ""))
    programme = None
    published = None
    if call:
        programme = clean_field(call.get("TitelEngelska"), 500)
        if _is_placeholder(programme):
            programme = clean_field(call.get("Titel"), 500)
        published, _ = parse_local_datetime(call.get("Publiceringsdatum"))

    return {
        "external_id": dnr,
        "title": title,
        "title_original": title_sv if title_sv != title else None,
        "description": description,
        "purpose_text": purpose,
        "eligibility_text": eligibility,
        "funding_text": funding,
        "category": classify(title, programme, purpose, description),
        "organisation": "Vinnova",
        "programme": programme,
        "source_url": f"{API}/ansokningsomgangar/{dnr}",
        "apply_url": apply_url,
        "language": language,
        "published_at": published,
        "opens_at": opens,
        "deadline_at": deadline,
        "deadline_status": deadline_status,
        "rolling_assessment": record.get("DagligAvlasning") == 1,
        "decision_expected_at": decision,
        "quality_flags": sorted(flags),
    }


def strip_personal_data(record: dict) -> dict:
    """Data minimisation: drop contact persons (names, e-mails, phone numbers) before storage."""
    return {k: v for k, v in record.items() if k not in ("KontaktLista",)}


class VinnovaCollector(Collector):
    key = "vinnova"

    def fetch_live(self, db: Session) -> dict:
        since = (today() - timedelta(days=LOOKBACK_DAYS)).isoformat()
        try:
            with self.client() as client:
                rounds = client.get(f"{API}/ansokningsomgangar/{since}").json()
                calls = client.get(f"{API}/utlysningar/{since}").json()
        except UrlRejected:
            raise
        except Exception as exc:  # noqa: BLE001
            raise SourceUnavailable(f"Vinnova API unavailable: {type(exc).__name__}") from exc
        if not isinstance(rounds, list) or not isinstance(calls, list):
            raise SourceUnavailable("Vinnova API returned an unexpected payload shape")
        return {"rounds": [strip_personal_data(r) for r in rounds if isinstance(r, dict)], "calls": [strip_personal_data(c) for c in calls if isinstance(c, dict)]}

    def ingest(self, db: Session, source: Source, payload: Any, mode: str, retrieved_at: datetime, stats: UpsertStats) -> None:
        if not isinstance(payload, dict) or not isinstance(payload.get("rounds"), list):
            raise SourceUnavailable("Vinnova payload missing 'rounds'")
        calls = {str(c.get("Diarienummer")): c for c in payload.get("calls", []) if isinstance(c, dict)}
        seen: set[str] = set()
        for raw in payload["rounds"]:
            stats.fetched += 1
            if not isinstance(raw, dict):
                stats.reject("malformed_record")
                continue
            record = parse_round(raw, calls, stats)
            if record is None:
                continue
            if record["external_id"] in seen:
                stats.reject("duplicate_in_payload")
                continue
            seen.add(record["external_id"])
            excerpt = record["purpose_text"] or record["description"]
            upsert_opportunity(db, source, record, mode=mode, retrieved_at=retrieved_at, stats=stats, evidence_excerpt=excerpt, reuse_note=REUSE_NOTE)
