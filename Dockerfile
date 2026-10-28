FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1
WORKDIR /build

COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m pip wheel --wheel-dir=/wheels .

FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    CAR_CATALOG_DATABASE_URL=sqlite:////app/data/car_catalog.db \
    CAR_CATALOG_ENVIRONMENT=production \
    HOST=0.0.0.0 \
    PORT=8000
WORKDIR /app

RUN groupadd --system appuser \
    && useradd --system --gid appuser --home-dir /app --no-create-home appuser \
    && mkdir -p /app/data \
    && chown -R appuser:appuser /app
COPY --from=builder /wheels /wheels
RUN python -m pip install --no-cache-dir --no-index --find-links=/wheels car-catalog \
    && rm -rf /wheels

USER appuser
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1

CMD ["car-catalog"]
