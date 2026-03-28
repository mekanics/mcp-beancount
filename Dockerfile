FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies (no dev deps, no editable install)
RUN uv sync --frozen --no-dev --no-editable

# Copy source
COPY src/ ./src/

# Install the package itself
RUN uv pip install --system --no-deps .

ENV BEANCOUNT_FILE=""
ENV BASE_CURRENCY=""
ENV ACCOUNT_ALLOWLIST=""
ENV BEANCOUNT_RELOAD="false"

ENTRYPOINT ["mcp-beancount"]
