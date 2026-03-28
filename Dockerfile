FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files first for layer caching
COPY pyproject.toml uv.lock ./

# Install all dependencies + the package itself into the system Python
RUN uv pip install --system --frozen .

# Copy source
COPY src/ ./src/

# Re-install the package itself (now with real source, no-deps since already installed)
RUN uv pip install --system --no-deps --no-editable .

ENV BEANCOUNT_FILE=""
ENV BASE_CURRENCY=""
ENV ACCOUNT_ALLOWLIST=""
ENV BEANCOUNT_RELOAD="false"

ENTRYPOINT ["mcp-beancount"]
