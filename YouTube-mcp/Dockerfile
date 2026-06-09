# --- Builder stage ---
FROM python:3.12-slim-bookworm AS builder
WORKDIR /app
COPY pyproject.toml /app/
RUN pip install --no-cache-dir --prefix=/install \
    'yt-dlp>=2024.12.0' 'mcp>=1.1.2' 'uvicorn[standard]>=0.24.0' 'starlette>=0.27.0' 'anyio>=3.7.0'

# --- Release stage ---
FROM python:3.12-slim-bookworm AS release
WORKDIR /app
COPY --from=builder /install /usr/local
COPY src/ /app/src/
ENV PORT=3000
EXPOSE 3000
CMD ["python", "-m", "uvicorn", "src.youtube_mcp.http_server:app", "--host", "0.0.0.0", "--port", "3000"]
