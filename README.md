<!--
Author:    mikomeller
Version:   0.1.7
Filename:  README.md
Pathname:  README.md
Purpose:   Overview, structure and first-time setup of 12_family_shopper_agent
-->
# 12_family_shopper_agent

A family shopping agent built on Affinidi **TrustBoris** for the AI Agents Berlin hackathon (Affinidi challenge).
It searches and compares products through the official **idealo MCP** and **orders on its own**,
within each member's and the family's monthly spending caps.

**Trust dividend:** spending money without a parent approving every order.

| Role | May do | Monthly cap |
|---|---|---|
| Parent | everything, approves requests, sets budgets | none (family cap applies) |
| Teen | search and order alone | €50 |
| Child | search; every order becomes an approval request | €20 |
| Family | all orders together | €400 |

Architecture: [`doc/diagrams/family_buyer_architecture.mmd`](doc/diagrams/family_buyer_architecture.mmd) ·
Purchase flow: [`doc/diagrams/purchase_decision_sequence.mmd`](doc/diagrams/purchase_decision_sequence.mmd) ·
Research: [`doc/research/affinidi_boris_idealo.md`](doc/research/affinidi_boris_idealo.md)

## Structure
```
.github/ISSUE_TEMPLATE/   Idea, Task, Bug issue forms
agent/                    family_buyer_system_prompt.md (system prompt of the shopping agent)
config/                   family_budget.example.yaml (copy to family_budget.yaml)
docker/boris/             Dockerfile + README for the Boris gateway
docker/app/               Dockerfile of the full application (web UI + wallet), see "Run everything in Docker"
compose.yaml              services `app` and `boris` (profile `boris`)
evals/                    eval harness (harness.py, drivers.py), scenarios S-01...S-13, L3/L4 tests, run_report.py, results/
doc/                      research, diagrams, design (wallet_mcp.md), agents, evals, handover, tasks
src/family_shopper/wallet/       Family Wallet MCP (stdio): db, identity (HMAC token), service, server
src/family_shopper/idealo_mock/  offline idealo MCP mock + fixtures
src/family_shopper/discount_check.py  discount sanity check
tests/                    pytest: caps (L1), MCP contract (L2), mock, demo, smoke
scripts/                  demo.py (offline demo), seed_wallet.py, wallet_tokens.py, ui_wallet_smoke.mjs, setup_github.py, board.py
src/server.js, src/wallet-client.js, src/idealo-oauth.js, src/cli.js   Node web UI backend (see Web UI)
web/, index.html, vite.config.js, package.json                        React front end
skills/family-shopper/    shopper skill used by the chat
```

## Run the tests and the offline demo
```bash
uv sync
uv run pytest -q
uv run python scripts/demo.py
```

## Run everything in Docker
```bash
docker compose up -d --build app      # builds and starts the web UI + wallet
# open http://localhost:6274           (the only published port, bound to 127.0.0.1 only; the demo sign-in is not authentication)
```
- The wallet database lives in the named volume `app-data` and is seeded on first start.
- Reset to a fresh state:
  `docker compose down && docker volume rm 12_family_shopper_agent_app-data && docker compose up -d app`
- An OpenAI key goes into `.env` in the repo root (git-ignored; never commit it). Without a key the chat runs in offline mode (see Web UI).
- Boris CLI: `docker compose --profile boris run --rm boris boris doctor`. The image contains the Docker client; `boris doctor` shows Docker OK.
  The `boris` service mounts `/var/run/docker.sock`, which gives that container control of the host's Docker (weakens isolation); use it only on request. `boris login` is not done yet (owner).
- Runbook: [`doc/runbooks/docker_app.md`](doc/runbooks/docker_app.md). The container serves the Vite dev server, not a production build.

## Web UI (by Rodrigo)
A chat front end for the family shopper. **Search uses the real idealo MCP and needs an OpenAI key.**
**All budget decisions come from the Family Wallet MCP** (integer cents; teen 50 EUR, child 20 EUR with parent approval, family 400 EUR per month).
The UI never decides a cap: the Node server starts one wallet process per member with a signed token and relays the wallet's answers.
```bash
npm install
cp .env.example .env     # set OPENAI_API_KEY; optionally WALLET_TOKEN_SECRET and WALLET_DB
npm run dev              # server on http://127.0.0.1:3001, UI via Vite
```
If `WALLET_TOKEN_SECRET` is empty the server generates a random one in memory at start. The wallet db is created on first start
(`WALLET_DB`, default `data/wallet.sqlite`). Members and limits are changed only in the wallet by a parent; the UI cannot add members.
`src/cli.js` (`npm start`) runs the older CLI, which still uses a local JSON budget and does not go through the wallet.
Smoke test with the server running: `node scripts/ui_wallet_smoke.mjs` (32 offline steps, 32 of 32 through the Docker endpoint). Budget-aware offers: `node scripts/offline_agent_budget_check.mjs` (6 of 6).

**Family accounts (demo sign-in).** The UI has an account switcher Parent / Teen / Child. The signed-in member (HTTP header `X-Family-Member`)
is the caller for chat, purchases, approve and reject; a `memberName` in the body cannot override it (403); a missing header gives 401.
Approve and reject reach the wallet as the signed-in member, so the wallet refuses non-parents. This is a DEMO sign-in, **not authentication**;
in production the caller identity must come from TrustBoris.

**Discount check.** When a "was" price is claimed, the server runs `check_discount` before the wallet call; an INFLATED verdict blocks the order.
The wallet has no price history and cannot verify a discount itself; an agent that skips the check is limited only by the caps.

**Budget-aware offers.** The wallet decides per offer (`check_budget(price_cents)` → `fits`) for the signed-in member. The offline assistant lists only offers that fit
and otherwise says "Nothing in this search fits your budget: the cheapest offer is …, you have … left this month" and suggests affordable catalogue items; the LLM tool path
filters `get_product_offers` results on the server (fails closed). Limits: mock search results carry no price and are not filtered; the live idealo catalogue is not filtered;
suggested alternatives are affordable items, not necessarily the same kind of product.

**Prices and discounts are checked by the server.** With the mock catalogue a purchase needs a known `productRef`; the server takes price, shop, link, product name and was-price
from the catalogue, and a client price that differs is refused (409). Only the verdicts GENUINE and NOT_BEST_PRICE proceed; INFLATED and unverifiable discounts are blocked.
Purchases against the LIVE idealo catalogue are refused (501) until the server can verify the price; `ALLOW_UNVERIFIED_LIVE_PURCHASES=1` overrides this (unverified path).
`/api/state` and the chat context are read as the signed-in member: teen and child see only their own orders, requests and budget line (plus the family totals).

**Model provider (parent only).** The "Model provider" dialog selects OpenAI / Codex API key (Responses API), Nebius Token Factory (base URL `https://api.tokenfactory.nebius.com/v1`,
from Nebius' docs; the default model name is a guess, check it in the Nebius console) or any OpenAI-compatible endpoint (Chat Completions tool loop). The key stays in server memory only,
is never returned (only the last 4 characters) or logged, is dropped when the base URL or provider changes and is gone after a restart; private and link-local base URLs are refused.
Env alternative in `.env`: `LLM_PROVIDER`, `LLM_BASE_URL`, `LLM_MODEL`, `LLM_API_KEY`. With a key but without idealo sign-in the model uses the mock catalogue.
Signing in with a ChatGPT/Codex subscription (OAuth) is not built; API keys only. Code: `src/llm-provider.js`.

**Demo links.** `?as=parent|teen|child` signs in as that member and `?q=<text>` fills the chat, e.g. `http://localhost:6274/?as=child&q=headphones`.

**Offline chat mode.** When `OPENAI_API_KEY` is unset, the chat answers deterministically from the idealo mock (no LLM) and the status endpoint reports `mode: "offline-mock"`.

**Not tested:** a real OpenAI key, a real Nebius key (the provider path ran only against the local fake server: `node scripts/fake_llm.mjs`, then `FAKE_LLM=1 node scripts/ui_wallet_smoke.mjs`, 43 of 43), live idealo OAuth,
the `ALLOW_UNVERIFIED_LIVE_PURCHASES` path, and the UI clicked through in a browser (headless screenshots at 1280px only; purchase status cards, approve/reject with a pending request, light theme,
a 390px phone with data, the provider dialog and keyboard focus were never seen rendered).

**Mock catalogue.** The idealo mock has 13 products (was 4) with fictional shops, shipping, delivery, EANs with valid check digits, 30-day histories, one product per discount verdict
and a second injection text in a shop note. The data is INVENTED (`_meta.source` says so); real idealo response shapes and prices are unverified until the live smoke test (#3).

## First-time GitHub setup (on your Mac, from `~/Documents/M1_20230921/src/genAI/12_family_shopper_agent`)
```bash
brew install gh                      # if missing
gh auth login                        # if not logged in as mikomeller
gh auth refresh -s project           # Projects scope
python3 scripts/setup_github.py --dry-run   # check, no network
python3 scripts/setup_github.py             # creates repo, labels, milestones, Project, fields, 40 issues (7 epics), epic links
```
The script creates the **private** repo `mikomeller/12_family_shopper_agent`, makes the first commit and pushes.
It is safe to re-run. If your Project already has another number, pass `--project-number <N>`.

Then, once, in the Project: **New view → Board → Column by: Stage**, and under **Workflows** enable
**Auto-add to project** for this repo so new issues land on the board.

## Branches
`main` is reserved for reviewed code and only changes through pull requests.
Every collaborator gets a branch named after their GitHub login, started from `main`:
```bash
python3 scripts/create_collaborator_branches.py --dry-run   # shows who gets which branch
python3 scripts/create_collaborator_branches.py
```
Covers accepted collaborators and pending invitations (owner skipped). Re-run after inviting new people.

## Before the hackathon kickoff
Docker running · `brew install --cask affinidi-ai/tap/boris` · `boris doctor` ·
`boris login --url https://trustboris.ai` · use Chrome (not Safari). See milestone **M0 Pre-kickoff**.
