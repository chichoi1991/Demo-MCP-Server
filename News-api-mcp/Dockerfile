# --- Builder stage ---
FROM python:3.12-slim-bookworm AS builder

WORKDIR /app

COPY pyproject.toml /app/

# Install all dependencies (including HTTP transport deps)
RUN pip install --no-cache-dir --prefix=/install \
    'httpx>=0.28.1' 'mcp>=1.1.2' 'uvicorn[standard]>=0.24.0' 'starlette>=0.27.0' 'anyio>=3.7.0'

# --- Release stage ---
FROM python:3.12-slim-bookworm AS release

WORKDIR /app

COPY --from=builder /install /usr/local
COPY src/ /app/src/

ENV PORT=3000

EXPOSE 3000

# Run via Streamable HTTP transport (not stdio)
# Single worker per replica; scale out via Container Apps replicas (min 3)
CMD ["python", "-m", "uvicorn", "src.news_api_mcp.http_server:app", "--host", "0.0.0.0", "--port", "3000"]
