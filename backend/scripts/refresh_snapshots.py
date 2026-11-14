"""Fetch live source data through the collectors and store it as offline snapshots.

Usage:  python -m scripts.refresh_snapshots
Snapshots are labelled 'snapshot' (previously collected) in the application, never 'live'.
"""
from __future__ import annotations

from datetime import timedelta

from app.core.clock import today, utcnow
from app.db.session import SessionLocal
from app.services.collectors.runner import get_collector
from app.services.collectors.vinnova import RECENT_CLOSE_GRACE_DAYS


def _filter_vinnova(payload: dict) -> dict:
    cutoff = (today() - timedelta(days=RECENT_CLOSE_GRACE_DAYS)).isoformat()
    oldest_open = (today() - timedelta(days=730)).isoformat()
    rounds = [
        r for r in payload["rounds"]
        if r.get("Publik") == 1
        and ((r.get("Stangningsdatum") or "") >= cutoff or (r.get("Stangningsdatum") or "").startswith("1900") or not r.get("Stangningsdatum"))
        and (r.get("Oppningsdatum") or "9999") >= oldest_open
    ]
    call_ids = {str(r.get("DiarienummerUtlysning")) for r in rounds}
    calls = [c for c in payload["calls"] if str(c.get("Diarienummer")) in call_ids]
    return {"rounds": rounds, "calls": calls}


def main() -> None:
    db = SessionLocal()
    try:
        for key in ("vinnova", "bsp_members", "bsp_news", "bsp_events"):
            collector = get_collector(key)
            payload = collector.fetch_live(db)
            if key == "vinnova":
                payload = _filter_vinnova(payload)
            size = len(payload["rounds"]) if key == "vinnova" else len(payload)
            path = collector.write_snapshot(payload, utcnow())
            print(f"{key}: {size} records -> {path.name}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
