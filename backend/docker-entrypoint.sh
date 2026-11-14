#!/bin/sh
set -e
echo "[vsp] waiting for database..."
python - <<'PY'
import time, sys
from sqlalchemy import text
from app.core.config import get_settings
from app.core.db_safety import DatabaseSafetyError
from app.db.session import make_engine
# Validates the URL (approved, non-protected database) before creating the engine; every connection then verifies
# the actual database name. Safety failures stop immediately instead of retrying. Passwords are never printed.
try:
    engine = make_engine(get_settings().database_url)
except DatabaseSafetyError as exc:
    sys.exit(f"[vsp] refusing to start: {exc}")
for attempt in range(60):
    try:
        with engine.connect() as c:
            c.execute(text("SELECT 1"))
        print("[vsp] database is ready")
        sys.exit(0)
    except DatabaseSafetyError as exc:
        sys.exit(f"[vsp] refusing to start: {exc}")
    except Exception as exc:
        print(f"[vsp] database not ready ({type(exc).__name__}); retrying ({attempt + 1}/60)")
        time.sleep(2)
sys.exit("[vsp] database did not become ready")
PY
echo "[vsp] applying migrations..."
alembic upgrade head
echo "[vsp] starting API on :8000 (seeds automatically on first start)"
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --proxy-headers
