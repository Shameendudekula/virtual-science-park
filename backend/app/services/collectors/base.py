"""Collector framework: fetch -> parse/validate -> idempotent upsert, with run tracking and source health."""
from __future__ import annotations

import json
import logging
from abc import ABC, abstractmethod
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import CollectionRun, Source, SourceHealth
from app.security.url_guard import SafeHttpClient
from app.services.collectors.registry import SOURCE_BY_KEY

log = logging.getLogger("vsp.collectors")
SNAPSHOT_DIR = Path(__file__).resolve().parents[2] / "seed" / "snapshots"


class SourceUnavailable(RuntimeError):
    """The external source could not be reached or returned unusable data."""


@dataclass
class UpsertStats:
    fetched: int = 0
    created: int = 0
    updated: int = 0
    unchanged: int = 0
    rejected: int = 0
    rejection_reasons: Counter = field(default_factory=Counter)

    def reject(self, reason: str) -> None:
        self.rejected += 1
        self.rejection_reasons[reason] += 1


class Collector(ABC):
    key: str

    def __init__(self, client_factory=None) -> None:  # noqa: ANN001
        self._client_factory = client_factory

    @property
    def definition(self):  # noqa: ANN201
        return SOURCE_BY_KEY[self.key]

    def client(self) -> SafeHttpClient:
        if self._client_factory:
            return self._client_factory(self.definition.allowed_hosts)
        return SafeHttpClient(self.definition.allowed_hosts)

    # ---- to implement --------------------------------------------------------------------
    @abstractmethod
    def fetch_live(self, db: Session) -> Any:
        """Fetch raw payload from the live source. Raise SourceUnavailable on failure."""

    @abstractmethod
    def ingest(self, db: Session, source: Source, payload: Any, mode: str, retrieved_at: datetime, stats: UpsertStats) -> None:
        """Parse, validate and upsert the payload. Must be idempotent."""

    # ---- snapshot support ----------------------------------------------------------------
    def snapshot_path(self) -> Path:
        return SNAPSHOT_DIR / f"{self.key}.json"

    def load_snapshot(self) -> tuple[Any, datetime]:
        path = self.snapshot_path()
        if not path.exists():
            raise SourceUnavailable(f"No snapshot available for {self.key}")
        data = json.loads(path.read_text(encoding="utf-8"))
        return data["payload"], datetime.fromisoformat(data["retrieved_at"])

    def write_snapshot(self, payload: Any, retrieved_at: datetime) -> Path:
        path = self.snapshot_path()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"source": self.key, "retrieved_at": retrieved_at.isoformat(), "payload": payload}, ensure_ascii=False, indent=1),
            encoding="utf-8",
        )
        return path


def get_source(db: Session, key: str) -> Source:
    source = db.scalar(select(Source).where(Source.key == key))
    if source is None:
        raise LookupError(f"Unknown source '{key}'")
    return source


def _health(db: Session, source: Source) -> SourceHealth:
    if source.health is None:
        source.health = SourceHealth(source_id=source.id)
        db.flush()
    return source.health


def run_collector(db: Session, collector: Collector, *, mode: str = "live", trigger: str = "manual") -> CollectionRun:
    """Run one collection. A failure never deletes or modifies existing records."""
    source = get_source(db, collector.key)
    run = CollectionRun(source_id=source.id, mode=mode, trigger=trigger, status="running", started_at=utcnow())
    db.add(run)
    db.flush()
    health = _health(db, source)
    health.last_attempt_at = run.started_at
    stats = UpsertStats()
    try:
        if mode == "live":
            payload = collector.fetch_live(db)
            retrieved_at = utcnow()
        else:
            payload, retrieved_at = collector.load_snapshot()
        with db.begin_nested():
            collector.ingest(db, source, payload, mode, retrieved_at, stats)
        run.status = "success" if stats.rejected == 0 or (stats.created + stats.updated + stats.unchanged) > 0 else "partial"
        health.last_success_at = utcnow() if mode == "live" else health.last_success_at
        health.consecutive_failures = 0
        health.last_error = None
        if mode == "live":
            health.data_mode = "live"
            health.status = "healthy"
        elif health.status in ("never_run", "failing"):
            health.status = "snapshot_only"
            health.data_mode = "snapshot"
    except Exception as exc:  # noqa: BLE001 - collectors must never crash the app
        run.status = "failed"
        run.error_message = f"{type(exc).__name__}: {str(exc)[:500]}"
        health.consecutive_failures += 1
        health.last_error = run.error_message
        health.status = "failing" if health.consecutive_failures >= 2 or health.last_success_at is None else "degraded"
        log.warning("collector failed", extra={"source": collector.key, "status": "failed"})
    run.finished_at = utcnow()
    run.records_fetched = stats.fetched
    run.records_created = stats.created
    run.records_updated = stats.updated
    run.records_unchanged = stats.unchanged
    run.records_rejected = stats.rejected
    run.rejection_reasons = dict(stats.rejection_reasons)
    health.record_count = collector_record_count(db, collector.key, source.id)
    db.commit()
    log.info(
        f"collection {collector.key} {run.status}: fetched={stats.fetched} created={stats.created} updated={stats.updated} "
        f"unchanged={stats.unchanged} rejected={stats.rejected}",
        extra={"source": collector.key, "run_id": run.id, "status": run.status},
    )
    return run


def collector_record_count(db: Session, key: str, source_id: int) -> int:
    from sqlalchemy import func

    from app.models import Company, Evidence, Opportunity

    if key == "bsp_members":
        return db.scalar(select(func.count(Company.id)).where(Company.bsp_member_id.is_not(None))) or 0
    if key == "company_websites":
        return db.scalar(select(func.count(Evidence.id)).where(Evidence.source_id == source_id)) or 0
    return db.scalar(select(func.count(Opportunity.id)).where(Opportunity.source_id == source_id)) or 0
