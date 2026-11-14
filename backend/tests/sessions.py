"""Session helpers for API tests.

Demo sessions (password-free) are read-only; changing company data needs a password session. Tests set a known,
test-only password on the seeded account (fast hash) and sign in through the real /api/auth/login endpoint."""
from __future__ import annotations

from sqlalchemy import select

from tests.conftest import company_id

TEST_PASSWORD = "test-only-password-4f9c"


def demo_headers(client, db, slug: str = "ocean-harvesting") -> dict:
    r = client.post("/api/auth/demo-login", json={"company_id": company_id(db, slug)})
    assert r.status_code == 200 and r.json()["read_only"] is True
    return {"Authorization": f"Bearer {r.json()['token']}"}


def password_headers(client, db, slug: str = "ocean-harvesting") -> dict:
    from app.models import CompanyAccount
    from app.security.auth import hash_password

    account = db.scalar(select(CompanyAccount).where(CompanyAccount.username == slug))
    account.password_hash = hash_password(TEST_PASSWORD, iterations=1_000)
    db.commit()
    r = client.post("/api/auth/login", json={"username": slug, "password": TEST_PASSWORD})
    assert r.status_code == 200 and r.json()["read_only"] is False, r.text
    return {"Authorization": f"Bearer {r.json()['token']}"}
