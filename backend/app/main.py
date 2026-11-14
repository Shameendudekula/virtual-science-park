"""Virtual Science Park API application."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import auth, companies, core
from app.core.config import get_settings
from app.core.logging import configure_logging
from app.models.company import SourceFactImmutableError

log = logging.getLogger("vsp.api")
MAX_BODY_BYTES = 64 * 1024


def _startup() -> None:
    settings = get_settings()
    if not settings.auto_seed:
        return
    from app.db.session import SessionLocal
    from app.seed.loader import is_seeded, retag_if_needed, seed_all, seed_companies, seed_sources
    from app.services.recommendations.pipeline import recompute_all

    db = SessionLocal()
    try:
        if not is_seeded(db):
            log.info("database empty: seeding sources, evidence-backed profiles and source snapshots")
            seed_all(db)
            log.info("seed complete")
        else:
            seed_sources(db)  # registry changes (e.g. new adapters) apply to existing databases
            added = seed_companies(db)  # additive: new evidence-backed claims shipped with the code
            db.commit()
            if retag_if_needed(db) or added:
                log.info("backfilled derived fields; recomputing intelligence")
                recompute_all(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_app: FastAPI):  # noqa: ANN201
    settings = get_settings()
    configure_logging(settings.log_level)
    for warning in settings.security_warnings():  # names settings, never values
        log.warning("security: %s", warning)
    _startup()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="Virtual Science Park API",
        version="1.0.0",
        description="Evidence-backed, explainable innovation intelligence for Blue Science Park companies. "
        "Every recommendation exposes its criteria, evidence and uncertainty.",
        lifespan=lifespan,
        docs_url="/api/docs",
        redoc_url="/api/redoc",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["GET", "POST", "PATCH", "PUT"],
        allow_headers=["Content-Type", "X-Admin-Token", "Authorization"],
        allow_credentials=False,
        max_age=600,
    )

    @app.middleware("http")
    async def security_and_logging(request: Request, call_next):  # noqa: ANN001, ANN202
        length = request.headers.get("content-length")
        if length and length.isdigit() and int(length) > MAX_BODY_BYTES:
            return JSONResponse({"error": {"code": "payload_too_large", "message": "Request body too large."}}, status_code=413)
        start = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Cache-Control"] = response.headers.get("Cache-Control", "no-store")
        log.info(f"{request.method} {request.url.path} {response.status_code}",
                 extra={"method": request.method, "path": request.url.path, "status": response.status_code,
                        "duration_ms": round((time.perf_counter() - start) * 1000, 1)})
        return response

    @app.exception_handler(HTTPException)
    async def http_error(_req: Request, exc: HTTPException) -> JSONResponse:
        code = {400: "bad_request", 401: "unauthorized", 403: "forbidden", 404: "not_found", 409: "conflict",
                413: "payload_too_large", 422: "unprocessable", 429: "rate_limited"}.get(exc.status_code, "error")
        return JSONResponse({"error": {"code": code, "message": str(exc.detail)}}, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_req: Request, exc: RequestValidationError) -> JSONResponse:
        details = [{"loc": [str(x) for x in e.get("loc", [])], "msg": e.get("msg")} for e in exc.errors()][:10]
        return JSONResponse({"error": {"code": "validation_error", "message": "Request validation failed.", "details": details}}, status_code=422)

    @app.exception_handler(SourceFactImmutableError)
    async def immutable(_req: Request, exc: SourceFactImmutableError) -> JSONResponse:
        return JSONResponse({"error": {"code": "conflict", "message": str(exc)}}, status_code=409)

    @app.exception_handler(Exception)
    async def unhandled(_req: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse({"error": {"code": "internal_error", "message": "An unexpected error occurred."}}, status_code=500)

    app.include_router(auth.router)
    app.include_router(core.router)
    app.include_router(companies.router)
    return app


app = create_app()
