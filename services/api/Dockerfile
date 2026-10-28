# syntax=docker/dockerfile:1
# The API image. Build from the repository root, since the API depends on packages/core:
#   docker build -f services/api/Dockerfile --build-arg GIT_SHA=$(git rev-parse HEAD) .

FROM python:3.12-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.12.19 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PYTHON_DOWNLOADS=0
WORKDIR /app

# Third-party dependencies first, so a code change doesn't reinstall them.
COPY pyproject.toml uv.lock README.md ./
COPY packages/core/pyproject.toml packages/core/README.md packages/core/
COPY services/api/pyproject.toml services/api/README.md services/api/
# The other workspace members' metadata only, so uv can check the lockfile; their code
# never enters the image.
COPY tools/pyproject.toml tools/README.md tools/
COPY ml/pyproject.toml ml/README.md ml/
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-install-workspace --package lugtolug-api

# Then the workspace packages, installed as wheels so the source isn't needed at runtime.
COPY packages/core/src packages/core/src
COPY services/api/src services/api/src
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable --package lugtolug-api

FROM python:3.12-slim
RUN useradd --system --uid 10001 --no-create-home app
COPY --from=build /app/.venv /app/.venv
# Last, so a new commit only changes this layer.
ARG GIT_SHA=unknown
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 GIT_SHA=${GIT_SHA}
USER app
EXPOSE 8080
CMD ["sh", "-c", "exec uvicorn lugtolug_api.main:app --host 0.0.0.0 --port ${PORT:-8080}"]
