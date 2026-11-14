"""Single source of 'now' so demos and tests are reproducible."""
from __future__ import annotations

from datetime import UTC, date, datetime

from app.core.config import get_settings


def utcnow() -> datetime:
    return datetime.now(UTC)


def today() -> date:
    ref = get_settings().reference_date.strip()
    if ref:
        return date.fromisoformat(ref)
    return utcnow().date()
