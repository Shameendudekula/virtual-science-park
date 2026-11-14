"""Collector behaviour: parsing/validation, idempotency, failure safety, provenance (reqs 9-11)."""
from __future__ import annotations

import json

import httpx
from sqlalchemy import func, select

from app.models import CollectionRun, Opportunity, Source
from app.security.url_guard import SafeHttpClient
from app.services.collectors.base import run_collector
from app.services.collectors.runner import get_collector
from app.services.collectors.vinnova import parse_round, strip_personal_data
from app.services.collectors.base import UpsertStats

ROUND = {
    "Diarienummer": "2026-99001", "DiarienummerUtlysning": "2026-99000", "Publik": 1,
    "Titel": "Vågkraft test", "TitelEngelska": "Wave energy demonstration call",
    "Beskrivning": "Beskrivning", "BeskrivningEngelska": "Funding for wave power demonstration projects.",
    "Oppningsdatum": "2026-10-01T00:00:00", "Stangningsdatum": "2027-02-01T14:00:00", "DagligAvlasning": 0,
    "UppskattatBeslutsdatum": None, "LankLista": [{"Beskrivning": "Ansök här", "URL": "https://ansok.vinnova.se/utlysning/abc"}],
    "WebTextLista": [{"TextID": 1, "TextEn": "Projects that demonstrate wave energy."},
                     {"TextID": 2, "TextEn": "At least two participants, one Swedish company."}],
    "KontaktLista": [{"Namn": "A Person", "Epost": "a.person@example.test", "Telefon": "08-000"}],
}
CALL = {"Diarienummer": "2026-99000", "TitelEngelska": "Energy programme", "Publiceringsdatum": "2026-09-01T10:00:00"}


def _transport(payloads: dict[str, object] | None = None, fail: bool = False) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if fail:
            raise httpx.ConnectError("simulated outage")
        for key, body in (payloads or {}).items():
            if key in str(request.url):
                return httpx.Response(200, json=body)
        return httpx.Response(404, json=[])
    return httpx.MockTransport(handler)


def _factory(transport):
    return lambda hosts: SafeHttpClient(hosts, transport=transport, resolver=lambda h: ["93.184.216.34"])


def test_parse_round_validation_rules():
    stats = UpsertStats()
    rec = parse_round(ROUND, {"2026-99000": CALL}, stats)
    assert rec["title"] == "Wave energy demonstration call" and rec["programme"] == "Energy programme"
    assert rec["eligibility_text"].startswith("At least two")
    assert rec["source_url"] == "https://data.vinnova.se/api/ansokningsomgangar/2026-99001"
    assert rec["apply_url"] == "https://ansok.vinnova.se/utlysning/abc"
    assert rec["deadline_status"] == "stated"
    placeholder = {**ROUND, "Diarienummer": "2026-99002", "TitelEngelska": "x", "Stangningsdatum": "1900-01-01T00:00:00"}
    rec2 = parse_round(placeholder, {}, stats)
    assert rec2["title"] == "Vågkraft test" and "english_title_missing" in rec2["quality_flags"]
    assert rec2["deadline_at"] is None and rec2["deadline_status"] == "placeholder_rejected"
    assert parse_round({**ROUND, "Publik": 0}, {}, stats) is None
    assert parse_round({**ROUND, "Diarienummer": "bad"}, {}, stats) is None
    assert stats.rejection_reasons["not_public"] == 1


def test_personal_data_is_not_collected():
    assert "KontaktLista" not in strip_personal_data(ROUND)
    assert "a.person@example.test" not in json.dumps(strip_personal_data(ROUND))


def test_repeated_collection_creates_no_duplicates(bare, db):
    collector = get_collector("vinnova", _factory(_transport({"ansokningsomgangar": [ROUND], "utlysningar": [CALL]})))
    first = run_collector(db, collector, mode="live")
    second = run_collector(db, collector, mode="live")
    assert first.status == "success" and first.records_created == 1
    assert second.records_created == 0 and second.records_unchanged == 1
    assert db.scalar(select(func.count(Opportunity.id)).where(Opportunity.external_id == "2026-99001")) == 1
    opp = db.scalar(select(Opportunity).where(Opportunity.external_id == "2026-99001"))
    assert opp.provenance == "live" and opp.evidence.url == opp.source_url


def test_changed_record_is_updated_in_place(bare, db):
    changed = {**ROUND, "BeskrivningEngelska": "Updated description for wave power demonstrations."}
    run = run_collector(db, get_collector("vinnova", _factory(_transport({"ansokningsomgangar": [changed], "utlysningar": [CALL]}))))
    assert run.records_updated == 1 and run.records_created == 0
    assert db.scalar(select(func.count(Opportunity.id)).where(Opportunity.external_id == "2026-99001")) == 1


def test_source_failure_keeps_existing_records(bare, db):
    before = db.scalar(select(func.count(Opportunity.id)))
    run = run_collector(db, get_collector("vinnova", _factory(_transport(fail=True))))
    assert run.status == "failed" and "unavailable" in run.error_message.lower()
    assert db.scalar(select(func.count(Opportunity.id))) == before
    src = db.scalar(select(Source).where(Source.key == "vinnova"))
    assert src.health.status in ("degraded", "failing") and src.health.last_error


def test_malformed_payload_fails_safely(bare, db):
    before = db.scalar(select(func.count(Opportunity.id)))
    run = run_collector(db, get_collector("vinnova", _factory(_transport({"ansokningsomgangar": {"unexpected": True}, "utlysningar": []}))))
    assert run.status == "failed"
    assert db.scalar(select(func.count(Opportunity.id))) == before


def test_snapshot_is_labelled_as_snapshot_not_live(bare, db):
    run = run_collector(db, get_collector("bsp_events"), mode="snapshot")
    assert run.status == "success" and run.mode == "snapshot"
    src = db.scalar(select(Source).where(Source.key == "bsp_events"))
    opps = db.scalars(select(Opportunity).where(Opportunity.source_id == src.id)).all()
    assert opps and all(o.provenance == "snapshot" for o in opps)
    assert all(o.source_url.startswith("https://www.bluesciencepark.se/") for o in opps)
    assert all(o.description is None and "metadata_only" in o.quality_flags for o in opps)


def test_disabled_sources_cannot_be_collected():
    import pytest

    for key in ("ymner", "eu_funding_tenders"):
        with pytest.raises(PermissionError):
            get_collector(key)


def test_runs_are_recorded(bare, db):
    assert db.scalar(select(func.count(CollectionRun.id))) >= 3
