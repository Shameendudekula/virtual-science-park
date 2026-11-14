FROM python:3.12-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends curl && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml ./
COPY app ./app
RUN pip install --upgrade pip && pip install ".[dev]"
COPY alembic.ini ./
COPY alembic ./alembic
COPY scripts ./scripts
COPY tests ./tests
COPY docker-entrypoint.sh ./
RUN chmod +x docker-entrypoint.sh && useradd --create-home --uid 10001 vsp && chown -R vsp /app
USER vsp
EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=5s --start-period=40s --retries=6 CMD ["sh", "-c", "curl -fsS http://localhost:${PORT:-8000}/api/health || exit 1"]
ENTRYPOINT ["./docker-entrypoint.sh"]
