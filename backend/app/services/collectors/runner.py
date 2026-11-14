"""Collector lookup and orchestration (collect -> recompute intelligence)."""
from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import CollectionRun
from app.services.collectors.base import Collector, run_collector
from app.services.collectors.bluesciencepark import BspEventsCollector, BspMembersCollector, BspNewsCollector
from app.services.collectors.evidence_verifier import EvidenceVerifierCollector
from app.services.collectors.registry import SOURCE_BY_KEY
from app.services.collectors.vinnova import VinnovaCollector

COLLECTORS: dict[str, type[Collector]] = {
    "vinnova": VinnovaCollector,
    "bsp_members": BspMembersCollector,
    "bsp_news": BspNewsCollector,
    "bsp_events": BspEventsCollector,
    "company_websites": EvidenceVerifierCollector,
}


def get_collector(key: str, client_factory=None) -> Collector:  # noqa: ANN001
    if key not in SOURCE_BY_KEY:
        raise LookupError(f"Unknown source '{key}'")
    definition = SOURCE_BY_KEY[key]
    if not definition.enabled:
        raise PermissionError(definition.disabled_reason or "Source is disabled")
    if not definition.collectable or key not in COLLECTORS:
        raise PermissionError("This source is not collectable")
    return COLLECTORS[key](client_factory=client_factory)


def collect(db: Session, key: str, *, mode: str = "live", trigger: str = "manual", recompute: bool = True, client_factory=None) -> CollectionRun:  # noqa: ANN001
    run = run_collector(db, get_collector(key, client_factory), mode=mode, trigger=trigger)
    if recompute and run.status in ("success", "partial") and (run.records_created or run.records_updated):
        from app.services.recommendations.pipeline import recompute_all

        recompute_all(db)
    return run
