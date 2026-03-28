FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install deps + package into a virtualenv
RUN uv sync --frozen --no-dev

# Copy source and re-sync so the package itself is installed from real source
COPY src/ ./src/
RUN uv sync --frozen --no-dev

# Put the venv on PATH so the entrypoint resolves correctly
ENV PATH="/app/.venv/bin:$PATH"

ENV BEANCOUNT_FILE=""
ENV BASE_CURRENCY=""
ENV ACCOUNT_ALLOWLIST=""
ENV BEANCOUNT_RELOAD="false"

ENTRYPOINT ["mcp-beancount"]
