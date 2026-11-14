"""Company workspace sign-in."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Company, CompanyAccount
from app.security.auth import SCOPE_READ, SCOPE_WRITE, Principal, PrincipalDep, issue_token, verify_password
from app.security.deps import rate_limit

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=1, max_length=200)


class DemoLoginRequest(BaseModel):
    company_id: int


def _session(company: Company, *, scope: str) -> dict:
    token, exp = issue_token(company.id, scope=scope)
    return {"token": token, "expires_at": exp, "read_only": scope != SCOPE_WRITE,
            "company": {"id": company.id, "name": company.name, "slug": company.slug}}


# Separate buckets: password attempts are limited strictly (brute force); opening demo workspaces is cheap and frequent.
@router.post("/login", dependencies=[Depends(rate_limit("login", 10, 60))], summary="Sign in to a company workspace (can edit)")
def login(body: LoginRequest, db: Session = Depends(get_db)) -> dict:
    account = db.scalar(select(CompanyAccount).where(CompanyAccount.username == body.username.strip().lower()))
    if account is None or not verify_password(body.password, account.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid username or password.")
    account.last_login_at = utcnow()
    db.commit()
    return _session(db.get(Company, account.company_id), scope=SCOPE_WRITE)


@router.post("/demo-login", dependencies=[Depends(rate_limit("demo-login", 60, 60))],
             summary="Demo mode only: open a demonstration company workspace without a password (read-only)")
def demo_login(body: DemoLoginRequest, db: Session = Depends(get_db)) -> dict:
    if not get_settings().demo_mode:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Demo login is disabled (DEMO_MODE=false). Use username and password.")
    company = db.get(Company, body.company_id)
    if company is None or company.profile_level not in ("full", "partial"):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No workspace exists for this company.")
    return _session(company, scope=SCOPE_READ)


@router.get("/me", summary="Current workspace session")
def me(principal: Principal = PrincipalDep, db: Session = Depends(get_db)) -> dict:
    company = db.get(Company, principal.company_id) if principal.company_id else None
    return {"authenticated": company is not None, "is_admin": principal.is_admin, "read_only": principal.read_only,
            "company": {"id": company.id, "name": company.name, "slug": company.slug} if company else None,
            "demo_mode": get_settings().demo_mode}
