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

# Run via Streamable HTTP transport (REST /query + MCP /mcp on same port)
CMD ["python", "-m", "uvicorn", "src.telecom_db_mcp.http_server:app", "--host", "0.0.0.0", "--port", "3000"]
