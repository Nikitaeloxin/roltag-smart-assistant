# app/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.22 /uv /uvx /bin/

# run as non-root: nothing in this app needs root inside the container.
# Ownership is set here, before anything is written into /app or /data —
# doing a `chown -R` *after* uv sync/COPY would force every already-written
# file to be copied into a new overlayfs layer just to change its owner,
# nearly doubling the image size.
RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /data/vectorstore /data/hf-cache \
    && chown -R appuser:appuser /app /data

USER appuser

# install uv and dependencies (uv.lock pins exact versions used locally,
# --frozen makes the build fail rather than silently re-resolve them)
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

# copy your source code
COPY --chown=appuser:appuser app/ app/

# Chroma persistence and the HuggingFace model cache (bge-m3 + reranker,
# downloaded on first use) should live outside the image, on volumes
# mounted at these paths via docker-compose.
ENV HF_HOME=/data/hf-cache

ENV LLM_BASE_URL=$LLM_BASE_URL

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
