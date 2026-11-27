# Author:    mikomeller
# Version:   0.1.3
# Filename:  Dockerfile
# Pathname:  docker/app/Dockerfile
# Purpose:   One image for the Family Shopper app: Node 22 (Vite UI + Express API) + Python 3.12 + uv (wallet MCP children).
#            Build context is the repo root (see compose.yaml).
FROM node:22-bookworm-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends python3 ca-certificates curl \
 && rm -rf /var/lib/apt/lists/*

# uv from the official image; it downloads/manages Python 3.12 itself (bookworm ships 3.11).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

WORKDIR /app
ENV UV_PYTHON=3.12 UV_PYTHON_INSTALL_DIR=/opt/uv-python UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy UV_COMPILE_BYTECODE=1 \
    UV_NO_SYNC=1

COPY package.json package-lock.json ./
RUN npm ci

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY . .

RUN useradd -m -u 10002 app && mkdir -p /data && chown -R app:app /data /app \
 && chmod -R a+rX /opt/uv-python /opt/venv
USER app

ENV PYTHONPATH=/app/src WALLET_DB=/data/wallet.sqlite NODE_ENV=development
VOLUME /data
EXPOSE 6274

# Dev server chosen: vite.config.js already proxies /api and /oauth to the API, so no code change is needed.
# (`npm run dev -- --host` would pass the flag to concurrently, not vite, so concurrently is called directly.)
# --host 0.0.0.0 overrides the config's "localhost" so the published port is reachable.
# UV_NO_SYNC: `uv run` must not re-sync (the project itself is used from PYTHONPATH, venv is read-only for the app user).
# First start seeds the demo wallet into the /data volume (the API rejects callers unknown to the wallet).
CMD ["sh", "-c", "[ -f \"$WALLET_DB\" ] || uv run python scripts/seed_wallet.py; exec npx concurrently -k npm:server 'npm:client -- --host 0.0.0.0'"]
