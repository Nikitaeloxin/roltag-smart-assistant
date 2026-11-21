FROM python:3.11-slim

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:0.11.22 /uv /uvx /bin/

# run as non-root: nothing in this app needs root inside the container.
RUN useradd --create-home --uid 1000 appuser  \
    && chown -R appuser:appuser /app

USER appuser

# install uv and dependencies (uv.lock pins exact versions used locally,
# --frozen makes the build fail rather than silently re-resolve them)
COPY --chown=appuser:appuser pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev

# copy your source code
COPY --chown=appuser:appuser main.py .
COPY --chown=appuser:appuser app/ app/

CMD ["uv", "run", "python", "main.py"]

