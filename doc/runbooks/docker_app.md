<!--
Author:    mikomeller
Version:   0.1.1
Filename:  docker_app.md
Pathname:  doc/runbooks/docker_app.md
Purpose:   Run the Family Shopper app (and optionally boris) in Docker; endpoint, reset, keys, verification status
-->
# Runbook: Family Shopper in Docker

Diagram: `doc/diagrams/docker_deployment.mmd`. Run all commands from the repo root.

Design: one image (Node 22 + Python 3.12 via uv + locked deps). The Vite **dev server** is used (not `vite build`) because
`vite.config.js` already proxies `/api` and `/oauth` to the Express API; a static build would need a new proxy. The API stays on
127.0.0.1:3001 inside the container; only port 6274 is published. First start seeds the demo wallet into the `/data` volume.

1. Build: `docker compose build`
2. Start: `docker compose up -d app` (wait until `docker compose ps` shows `healthy`).
3. Endpoint: open **http://localhost:6274** (exactly this host and port; the idealo OAuth callback is `http://localhost:6274/oauth/callback`).
   API calls need the header `X-Family-Member: parent|teen|child`, e.g.
   `curl -H "X-Family-Member: teen" http://localhost:6274/api/state`.
4. Pick up code changes (source is copied at build time): `docker compose up -d --build app`
5. Reset the wallet: `docker compose down && docker volume rm 12_family_shopper_agent_app-data && docker compose up -d app`
   (the volume name is prefixed with the compose project name; check `docker volume ls`).
   Or, for the demo: set `ALLOW_DEMO_RESET=1` (already set for the `app` service in `compose.yaml`; off by default, the endpoint then returns 404). "Play again" in the story UI calls `POST /api/demo/reset` (parent only, body `{"confirm":"reset-demo-wallet"}`). It runs `scripts/reset_demo_wallet.py`, which in one transaction deletes all orders and approval requests and restores the caps (400/50/20). The database file, the members and the tokens stay; no restart. To disable it, remove `ALLOW_DEMO_RESET` from `compose.yaml` and run `docker compose up -d --force-recreate app`. It is not a chat tool: the model cannot call it.
6. OpenAI key (optional; without it the app runs in offline mock mode): create `.env` in the repo root with
   `OPENAI_API_KEY=sk-...` (optionally `WALLET_TOKEN_SECRET=...`), then `docker compose up -d --force-recreate app`.
   `.env` is excluded from the image by `.dockerignore`; compose passes it at run time. A missing `.env` is fine.
7. Boris CLI (profile `boris`, starts only on request):
   - `docker compose --profile boris run --rm boris boris --version`
   - `docker compose --profile boris run --rm boris boris doctor`
   - Login: `docker compose --profile boris run --rm boris boris login --device` (check `boris login --help` for the exact flag);
     credentials persist in the `boris-home` volume.
   - **Security note:** the boris service mounts `/var/run/docker.sock` and joins group 0. That gives the container control of the
     host's Docker, which weakens the isolation you asked for. It is only needed for commands that host agents in Docker; remove
     the mount from `compose.yaml` if you do not use them.
8. Stop: `docker compose down` (keeps volumes).

## Verified (real output, 2026-11-27, macOS, Docker Desktop 29.9.3)
- `docker compose --profile boris build` succeeds; `app` becomes `healthy`.
- Host `curl http://localhost:6274/` returns 200; `/api/state` without the header returns 401, with `X-Family-Member: teen` returns members and caps.
- `POST /api/family/mock-purchases` through the proxy recorded "Docker Smoke" for Teen (40,01 EUR remained).
- `boris --version` prints `boris 0.1.35`; `boris doctor` reports Docker `29.9.3, Docker Desktop` through the socket mount.

## Not verified
- OpenAI-backed chat (no key used), the idealo OAuth callback flow, `boris login --device`, the idealo mock MCP child (not present at test time), amd64 builds.
