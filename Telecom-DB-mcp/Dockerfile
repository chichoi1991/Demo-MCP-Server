# --- Builder stage ---
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

COPY pyproject.toml /app/

# Install all runtime dependencies into a portable prefix
RUN pip install --no-cache-dir --prefix=/install \
    'duckdb>=1.0.0' 'mcp>=1.1.2' 'uvicorn[standard]>=0.24.0' \
    'starlette>=0.27.0' 'anyio>=3.7.0'

# --- Release stage ---
FROM python:3.12-slim-bookworm AS release

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ /app/src/
COPY data/ /app/data/

ENV PORT=3000
ENV TELECOM_CSV_PATH=/app/data/telecom_device_analysis_dummy_data.csv

EXPOSE 3000

# Run via Streamable HTTP transport (REST /query + MCP /mcp on same port).
# Concurrency tuning for ~100 concurrent callers per replica:
#   --workers 1               : keep a single in-memory DuckDB connection per replica
#                               (DuckDB threads handle CPU parallelism internally)
#   --limit-concurrency 200   : cap in-flight requests to protect memory
#   --backlog 2048            : larger accept queue for bursty traffic
#   --timeout-keep-alive 30   : reuse TCP connections across MCP calls
CMD ["python", "-m", "uvicorn", "src.telecom_db_mcp.http_server:app", \
     "--host", "0.0.0.0", \
     "--port", "3000", \
     "--workers", "1", \
     "--limit-concurrency", "200", \
     "--backlog", "2048", \
     "--timeout-keep-alive", "30"]
