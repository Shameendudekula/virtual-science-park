"""Opportunities, technologies, sources, collectors, recommendations actions, evidence, search, demo and health."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import Session

from app.api.serializers import evidence_out, opportunity_out, recommendation_out
from app.core.clock import today, utcnow
from app.core.config import get_settings
from app.db.session import get_db
from app.models import (
    CollectionRun,
    Company,
    Evidence,
    Opportunity,
    Recommendation,
    SavedRecommendation,
    Source,
    SourceHealth,
    Technology,
)
from app.schemas.api import RecommendationAction
from app.security.auth import Principal, PrincipalDep, require_company
from app.security.deps import rate_limit, require_admin, require_admin_unless_demo
from app.services.intelligence.profile import build_profile, load_company
from app.services.matching.opportunity_matching import score_opportunity

router = APIRouter(prefix="/api")


# --------------------------------------------------------------------------------------------- health
@router.get("/health", tags=["system"], summary="Service health")
def health(db: Session = Depends(get_db)) -> dict:
    s = get_settings()
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # noqa: BLE001
        db_ok = False
    counts = {}
    if db_ok:
        counts = {
            "companies_profiled": db.scalar(select(func.count(Company.id)).where(Company.profile_level.in_(("full", "partial")))) or 0,
            "companies_directory": db.scalar(select(func.count(Company.id)).where(Company.profile_level == "directory")) or 0,
            "opportunities": db.scalar(select(func.count(Opportunity.id))) or 0,
            "evidence": db.scalar(select(func.count(Evidence.id))) or 0,
        }
    return {"status": "ok" if db_ok else "degraded", "database": "ok" if db_ok else "unavailable", "version": "1.0.0",
            "demo_mode": s.demo_mode, "llm": {"enabled": s.llm_enabled, "provider": s.llm_provider if s.llm_enabled else None},
            "admin_actions_enabled": bool(s.admin_token.get_secret_value()), "today": today().isoformat(), "counts": counts}


# --------------------------------------------------------------------------------------------- member directory
@router.get("/members", tags=["companies"], summary="Blue Science Park member directory with profile status")
def members(db: Session = Depends(get_db)) -> dict:
    from app.services.intelligence.views import member_directory

    return member_directory(db)


# --------------------------------------------------------------------------------------------- opportunities
@router.get("/opportunities", tags=["opportunities"], summary="All collected opportunities")
def list_opportunities(
    category: str | None = None, source: str | None = None, q: str | None = Query(default=None, max_length=100),
    page: int = Query(1, ge=1), page_size: int = Query(50, ge=1, le=100), db: Session = Depends(get_db),
) -> dict:
    stmt = select(Opportunity).join(Source)
    if category:
        stmt = stmt.where(Opportunity.category == category)
    if source:
        stmt = stmt.where(Source.key == source)
    if q:
        stmt = stmt.where(or_(Opportunity.title.ilike(f"%{q}%"), Opportunity.description.ilike(f"%{q}%")))
    total = db.scalar(select(func.count()).select_from(stmt.subquery())) or 0
    rows = db.scalars(stmt.order_by(Opportunity.deadline_at.asc().nulls_last(), Opportunity.id).offset((page - 1) * page_size).limit(page_size)).all()
    return {"items": [opportunity_out(o) for o in rows], "total": total, "page": page, "page_size": page_size}


@router.get("/opportunities/{opportunity_id}", tags=["opportunities"], summary="Opportunity detail (optionally matched to a company)")
def get_opportunity(opportunity_id: int, company_id: int | None = None, db: Session = Depends(get_db),
                    principal: Principal = PrincipalDep) -> dict:
    o = db.get(Opportunity, opportunity_id)
    if o is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Opportunity {opportunity_id} not found")
    match = None
    if company_id is not None:
        require_company(company_id, principal)
        c = load_company(db, company_id)
        if c is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"Company {company_id} not found")
        if c.profile_level in ("full", "partial"):
            match = score_opportunity(build_profile(c), o, today())
    d = opportunity_out(o, match)
    d["evidence"] = evidence_out(o.evidence)
    return d


# --------------------------------------------------------------------------------------------- technologies
@router.get("/technologies", tags=["technologies"], summary="Technology taxonomy")
def list_technologies(db: Session = Depends(get_db)) -> list[dict]:
    counts = dict(db.execute(text("SELECT technology_id, count(*) FROM opportunity_technologies GROUP BY technology_id")).all())
    return [{"id": t.id, "key": t.key, "name": t.name, "area": t.area, "description": t.description, "opportunity_mentions": counts.get(t.id, 0)}
            for t in db.scalars(select(Technology).order_by(Technology.area, Technology.name))]


# --------------------------------------------------------------------------------------------- sources & collectors
def _source_out(s: Source, h: SourceHealth | None) -> dict:
    return {
        "key": s.key, "name": s.name, "publisher": s.publisher, "source_type": s.source_type, "base_url": s.base_url,
        "description": s.description, "license_note": s.license_note, "enabled": s.enabled, "collectable": s.collectable,
        "llm_allowed": s.llm_allowed, "disabled_reason": s.disabled_reason, "allowed_hosts": s.allowed_hosts,
        "health": {
            "status": h.status if h else "unknown", "data_mode": h.data_mode if h else None,
            "last_attempt_at": h.last_attempt_at.isoformat() if h and h.last_attempt_at else None,
            "last_success_at": h.last_success_at.isoformat() if h and h.last_success_at else None,
            "last_error": h.last_error if h else None, "consecutive_failures": h.consecutive_failures if h else 0,
            "record_count": h.record_count if h else 0,
        },
    }


@router.get("/sources", tags=["sources"], summary="Source registry")
def list_sources(db: Session = Depends(get_db)) -> list[dict]:
    return [_source_out(s, s.health) for s in db.scalars(select(Source).order_by(Source.id))]


@router.get("/sources/health", tags=["sources"], summary="Source health and recent collection runs")
def sources_health(limit: int = Query(25, ge=1, le=100), db: Session = Depends(get_db)) -> dict:
    sources = {s.id: s for s in db.scalars(select(Source))}
    runs = db.scalars(select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(limit)).all()
    return {
        "sources": [_source_out(s, s.health) for s in sources.values() if s.collectable],
        "runs": [{"id": r.id, "source_key": sources[r.source_id].key, "mode": r.mode, "trigger": r.trigger, "status": r.status,
                  "started_at": r.started_at.isoformat(), "finished_at": r.finished_at.isoformat() if r.finished_at else None,
                  "fetched": r.records_fetched, "created": r.records_created, "updated": r.records_updated,
                  "unchanged": r.records_unchanged, "rejected": r.records_rejected, "rejection_reasons": r.rejection_reasons,
                  "error": r.error_message} for r in runs],
    }


@router.post("/collectors/{source_name}/run", tags=["sources"], summary="Run a collector (admin token required)",
             dependencies=[Depends(require_admin), Depends(rate_limit("collect", 6, 60))])
def run_collector_endpoint(source_name: str, mode: str = Query("live", pattern="^(live|snapshot)$"), db: Session = Depends(get_db)) -> dict:
    from app.services.collectors.runner import collect

    try:
        run = collect(db, source_name, mode=mode, trigger="manual")
    except LookupError as exc:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    return {"id": run.id, "source": source_name, "mode": run.mode, "status": run.status, "fetched": run.records_fetched,
            "created": run.records_created, "updated": run.records_updated, "unchanged": run.records_unchanged,
            "rejected": run.records_rejected, "rejection_reasons": run.rejection_reasons, "error": run.error_message,
            "message": "Existing records were kept unchanged." if run.status == "failed" else "Collection completed."}


@router.get("/notifications", tags=["system"], summary="Recent source updates")
def notifications(db: Session = Depends(get_db)) -> list[dict]:
    sources = {s.id: s for s in db.scalars(select(Source))}
    out = []
    for r in db.scalars(select(CollectionRun).order_by(CollectionRun.started_at.desc()).limit(8)):
        src = sources[r.source_id]
        if r.status == "failed":
            msg = f"{src.name}: collection failed — existing data kept."
        elif r.mode == "snapshot":
            msg = f"{src.name}: loaded {r.records_created + r.records_updated + r.records_unchanged} records from snapshot."
        else:
            msg = f"{src.name}: {r.records_created} new, {r.records_updated} updated records."
        out.append({"id": r.id, "level": "error" if r.status == "failed" else "info", "message": msg, "at": r.started_at.isoformat(),
                    "mode": r.mode})
    return out


# --------------------------------------------------------------------------------------------- recommendations
def _rec(db: Session, rec_id: int, principal: Principal) -> Recommendation:
    r = db.get(Recommendation, rec_id)
    if r is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Recommendation {rec_id} not found")
    require_company(r.company_id, principal)
    return r


def _set_status(db: Session, rec_id: int, new_status: str, note: str | None, principal: Principal) -> dict:
    r = _rec(db, rec_id, principal)
    r.status = new_status
    r.status_changed_at = utcnow()
    saved = db.scalar(select(SavedRecommendation).where(SavedRecommendation.recommendation_id == r.id))
    if new_status == "saved" and saved is None:
        db.add(SavedRecommendation(recommendation_id=r.id, company_id=r.company_id, note=note, saved_at=utcnow()))
    elif new_status != "saved" and saved is not None:
        db.delete(saved)
    db.commit()
    return recommendation_out(r)


@router.get("/recommendations/{recommendation_id}", tags=["recommendations"], summary="Recommendation detail with evidence")
def get_recommendation(recommendation_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    r = _rec(db, recommendation_id, principal)
    d = recommendation_out(r)
    ids = r.detail.get("evidence_ids", [])
    claim_ids = r.detail.get("claim_ids", [])
    from app.models import CompanyClaim

    claims = db.scalars(select(CompanyClaim).where(CompanyClaim.id.in_(claim_ids))).all() if claim_ids else []
    for c in claims:
        if c.evidence_id:
            ids.append(c.evidence_id)
    d["evidence"] = [evidence_out(e) for e in db.scalars(select(Evidence).where(Evidence.id.in_(set(ids))))] if ids else []
    from app.api.serializers import claim_out

    d["claims"] = [claim_out(c) for c in claims]
    return d


@router.post("/recommendations/{recommendation_id}/save", tags=["recommendations"])
def save_recommendation(recommendation_id: int, body: RecommendationAction | None = None, db: Session = Depends(get_db),
                           principal: Principal = PrincipalDep) -> dict:
    return _set_status(db, recommendation_id, "saved", body.note if body else None, principal)


@router.post("/recommendations/{recommendation_id}/dismiss", tags=["recommendations"])
def dismiss_recommendation(recommendation_id: int, body: RecommendationAction | None = None, db: Session = Depends(get_db),
                           principal: Principal = PrincipalDep) -> dict:
    return _set_status(db, recommendation_id, "dismissed", body.note if body else None, principal)


@router.post("/recommendations/{recommendation_id}/explore", tags=["recommendations"], summary="Mark as explored")
def explore_recommendation(recommendation_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    return _set_status(db, recommendation_id, "explored", None, principal)


@router.post("/recommendations/{recommendation_id}/restore", tags=["recommendations"], summary="Return to open")
def restore_recommendation(recommendation_id: int, db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> dict:
    return _set_status(db, recommendation_id, "open", None, principal)


# --------------------------------------------------------------------------------------------- evidence
@router.get("/evidence", tags=["evidence"], summary="Evidence records by id")
def list_evidence(ids: str = Query(..., max_length=500), db: Session = Depends(get_db)) -> list[dict]:
    try:
        id_list = [int(x) for x in ids.split(",") if x.strip()][:50]
    except ValueError as exc:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "ids must be a comma-separated list of integers") from exc
    return [evidence_out(e) for e in db.scalars(select(Evidence).where(Evidence.id.in_(id_list)))]


@router.get("/evidence/{evidence_id}", tags=["evidence"])
def get_evidence(evidence_id: int, db: Session = Depends(get_db)) -> dict:
    e = db.get(Evidence, evidence_id)
    if e is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Evidence {evidence_id} not found")
    return evidence_out(e)  # type: ignore[return-value]


# --------------------------------------------------------------------------------------------- search & demo
@router.get("/search", tags=["search"], summary="Natural-language search over VSP data",
            dependencies=[Depends(rate_limit("search", 60, 60))])
def search(q: str = Query(..., min_length=2, max_length=300), company_id: int | None = None, db: Session = Depends(get_db),
           principal: Principal = PrincipalDep) -> dict:
    """Company-specific answers (and question history) require that company's workspace session."""
    from app.models import SearchHistory
    from app.services.intelligence.search import run

    if company_id is not None:
        require_company(company_id, principal)
    result = run(db, q, company_id, viewer_id=principal.company_id)
    named = result["query"]["company_id"]
    if named is not None and not principal.can_access(named):
        result = run(db, q, None, viewer_id=principal.company_id, public_only=True)
        result["note"] += " Company-specific ranking is only available inside that company's workspace; showing public results."
    if principal.company_id:
        db.add(SearchHistory(company_id=principal.company_id, query=q[:300], intent=result["query"]["intent"],
                             result_count=result["count"], created_at=utcnow()))
        db.commit()
    return result


@router.get("/search/history", tags=["search"], summary="Question history of the signed-in company workspace")
def search_history(db: Session = Depends(get_db), principal: Principal = PrincipalDep) -> list[dict]:
    from app.models import SearchHistory

    if principal.company_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to a company workspace to see its question history.")
    rows = db.scalars(select(SearchHistory).where(SearchHistory.company_id == principal.company_id)
                      .order_by(SearchHistory.created_at.desc()).limit(15))
    return [{"id": r.id, "query": r.query, "intent": r.intent, "result_count": r.result_count, "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/demo/reset", tags=["system"], summary="Reset the demo workspace (keeps collected source data)",
             dependencies=[Depends(require_admin_unless_demo), Depends(rate_limit("reset", 10, 60))])
def demo_reset(db: Session = Depends(get_db)) -> dict:
    from app.seed.loader import reset_demo

    return {"status": "reset", **reset_demo(db)}
