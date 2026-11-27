<!--
Author:    mikomeller, rhaveen-sa
Version:   0.1.14
Filename:  README.md
Pathname:  README.md
Purpose:   Overview, structure and first-time setup of 12_family_shopper_agent
-->
# Family Shopper Agent

Pocket money with guardrails. A shopping agent for the whole family: it searches idealo, compares shops and orders.
Teen and child order on their own up to their monthly budget. Above it a parent steps in. Nobody spends more than the family allows.

Built for the AI Agents Berlin hackathon, Affinidi TrustBoris challenge (27 Nov 2026).
Pitch deck (live): https://mikomeller.github.io/12_family_shopper_agent/ (source [`pitch/pitch.html`](pitch/pitch.html)) · 2 minute script: [`pitch/pitch_script_2min.md`](pitch/pitch_script_2min.md) ·
Website design: [`doc/design/website_design.md`](doc/design/website_design.md)

## What it does
| Who | What the agent does alone | Limit per month |
|---|---|---|
| Teen | searches, compares, orders up to the budget; above it the wallet refuses and a parent steps in | 50 € |
| Child | searches, compares, orders up to the budget; above it the wallet refuses and a parent steps in | 20 € |
| Parent | approves or rejects requests, sets limits, chooses the model | family limit applies |
| Whole family | all orders together, parent-approved ones included | 400 € |

Up to the budget the trust layer decides. Above it, a parent steps in: the member asks (button **Ask a parent**, route `POST /api/family/request-approval`, chat tool `request_parent_approval`), the parent approves or rejects. A parent-approved order counts against the member's budget and the family budget.

- **Live product search.** The app signs in to the official idealo MCP (`https://mcp.idealo.com/mcp`) with OAuth and searches real offers and price history.
- **Your own model.** A parent enters the provider, model and API key in the app: OpenAI, Nebius Token Factory or any OpenAI-compatible endpoint.
  The key stays in server memory. It is never written to disk and never sent back to the browser.
- **Limits in the wallet, not in the prompt.** Every order goes through our Family Wallet MCP. It counts money in whole cents and checks
  the limit and writes the order in one database step. It refuses an order above a member's budget, a forged caller and an approval from a non-parent, whatever the model asks.
- **The server checks every price.** The model only names what to buy. The server looks up the price, shop and link itself.
  On the sample catalogue it also checks a claimed "was" price against the price history and blocks an inflated discount.
- **Every "no" explains itself:** what was refused, why and how much is left this month.

## Get started
With Docker:
```bash
docker compose up -d --build app
```
Open `http://localhost:6274`. Then:
1. Sign in as **Parent** with the account switcher at the top.
2. Open **Bring your own model**. Choose the provider, enter the model and your API key.
3. Choose **Connect idealo** and sign in in idealo's window.
4. Switch to **Teen** or **Child** and ask for a product.

Guided story: open `http://localhost:6274/?story=1` and press **Play the story**. Case 1: the child asks for *Der Hobbit*, the idealo comparison highlights the best offer, the child orders within the budget. Case 2: a board game (30,98 €) is above the budget and refused, the child asks a parent, the parent approves and the family budget pays. Case 3: the teen wants a 79,99 € coffee machine, above the 50 € budget, so it is refused and a parent steps in and approves (added 2026-11-27 evening; replayed in headless Chrome on 2026-11-27 evening: 14 steps passed; wallet afterwards: three orders, child 0,00 €, teen 0,00 €, family 278,04 € left). Story flow (PR #74): a "now" banner ("Case x of 3 · Step y of 14"), the decision trail grouped into three collapsible cases with outcome chips, and a "Story finished" summary with a table and "Budgets after the story". **Play again** (and a first play on a used wallet) asks "Reset the demo wallet and play again?" and then calls `POST /api/demo/reset`. That endpoint works only with `ALLOW_DEMO_RESET=1` (set for the demo container in `compose.yaml`; off by default, then 404), only for a parent (403) and only with the body `{"confirm":"reset-demo-wallet"}` (400). It also needs an `Origin` header of the app's own page (`APP_ORIGINS`, default `http://localhost:6274` and `http://127.0.0.1:6274`; otherwise 403): this stops other web pages, but a local program can still forge the header, so the reset stays demo-only, parent-only and confirmation-gated. It deletes all orders and approval requests and restores the caps (400/50/20); members and tokens stay. Check the story in headless Chrome: `node scripts/story_replay.mjs http://localhost:6274/` (exit 0 only when "Story finished" appears). The Docker command below stays as the fallback. TrustBoris is not connected in the demo: the gateway steps in the story are simulated and labelled so; the limits are enforced by the Family Wallet.

Without Docker:
```bash
npm install
uv sync
cp .env.example .env     # optional: preset the provider, model and key here instead of in the app
npm run dev              # server on http://127.0.0.1:3001, UI through Vite
```
Without a model key the chat answers from a built-in sample catalogue, so you can try the flow offline.
The app shows which mode is active.

## How it works
```
Parent / Teen / Child  →  web app (React + Node)  →  your LLM (OpenAI, Nebius or any OpenAI-compatible endpoint)
                                   │
                   ┌───────────────┴───────────────┐
             idealo MCP (live, read only)    Family Wallet MCP (Python, SQLite)
             search, offers, price history   limits, orders, requests, approve, reject
```
- The Node server starts one wallet process per family member, each with a signed member token. The browser never decides a limit.
- Orders are recorded in the wallet with the shop and a link to the offer. The app does not pay the shop.
- With the live idealo catalogue the server cannot yet verify a price to the cent, so it refuses the order by default.
  Set `ALLOW_UNVERIFIED_LIVE_PURCHASES=1` to record live orders anyway (marked `priceVerified: false`). Search and comparison are live either way.
- Diagrams: [`doc/diagrams/family_buyer_architecture.mmd`](doc/diagrams/family_buyer_architecture.mmd),
  [`doc/diagrams/purchase_decision_sequence.mmd`](doc/diagrams/purchase_decision_sequence.mmd).
  Research: [`doc/research/affinidi_boris_idealo.md`](doc/research/affinidi_boris_idealo.md).

## Where TrustBoris fits
The wallet keeps the money safe on its own. TrustBoris controls the agent around it:
| Boris feature | Why we use it |
|---|---|
| Caller identity | the wallet needs to know who is calling to apply the right limit |
| Tools shown per role | a teen's or child's agent never sees `approve_request`, `reject_request` or `set_budget` |
| Prompt and reply screening | product texts from idealo are untrusted input |
| Throttle and response cache | protects the idealo quota (500 calls a day) and the model budget |
| Backup model | shopping keeps working when one model provider fails |

Status: Boris is designed in and the Boris CLI runs in Docker. The agent is not yet connected in Boris Agent Builder.

## Tested
```bash
uv run pytest -q                 # 191 passed, 16 skipped (the skipped tests need an LLM key)
uv run python scripts/demo.py    # walks the main flows against the real wallet, ends with DEMO OK: 5/5 scenes
```
- Limit rules and the wallet tool contract (L1/L2): 71 of 71 pass.
- 16 scenario files (S-01 to S-13, S-15, S-16, S-17), 3 runs each, with a scripted driver and a driver that breaks every rule: all pass, no limit was ever exceeded,
  no order went through above a member's budget without a parent's approval. Results: `evals/results/`.

## Known limits
- The account switcher (Parent, Teen, Child) is a simple sign-in, not authentication. Real caller identity should come from TrustBoris.
- Orders are recorded, not paid. Payment could come later from Affinidi Agent Pay.
- Live idealo orders need `ALLOW_UNVERIFIED_LIVE_PURCHASES=1` until the server can verify live prices. The discount check runs on the sample catalogue only.
- The scenario evals run at the tool layer, not yet with a language model.

## Structure
```
.github/ISSUE_TEMPLATE/   Idea, Task, Bug issue forms
agent/                    family_buyer_system_prompt.md (system prompt of the shopping agent)
config/                   family_budget.example.yaml (copy to family_budget.yaml)
docker/boris/             Dockerfile + README for the Boris gateway
docker/app/               Dockerfile of the full application (web UI + wallet), see "Run everything in Docker"
compose.yaml              services `app` and `boris` (profile `boris`)
evals/                    eval harness (harness.py, drivers.py), scenarios S-01...S-13, S-15...S-17, L3/L4 tests, run_report.py, results/
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

## For the team: tests and the offline walk-through
```bash
uv sync
uv run pytest -q
uv run python scripts/demo.py
```

## For the team: Docker details
```bash
docker compose up -d --build app      # builds and starts the web UI + wallet
# open http://localhost:6274           (the only published port, bound to 127.0.0.1 only; the demo sign-in is not authentication)
```
- The wallet database lives in the named volume `app-data` and is seeded on first start.
- Reset to a fresh state:
  `docker compose down && docker volume rm 12_family_shopper_agent_app-data && docker compose up -d app`
- A model key can go into `.env` in the repo root (git-ignored; never commit it) or be entered in the app by a parent.
- Boris CLI: `docker compose --profile boris run --rm boris boris doctor`. The image contains the Docker client; `boris doctor` shows Docker OK.
  The `boris` service mounts `/var/run/docker.sock`, which gives that container control of the host's Docker (weakens isolation); use it only on request. `boris login` is not done yet (owner).
- Runbook: [`doc/runbooks/docker_app.md`](doc/runbooks/docker_app.md). The container serves the Vite dev server, not a production build.

## For the team: web app details (web UI by Rodrigo)
- If `WALLET_TOKEN_SECRET` is empty the server generates a random one in memory at start. The wallet db is created on first start
  (`WALLET_DB`, default `data/wallet.sqlite`). Members and limits change only in the wallet, by a parent.
- The signed-in member (HTTP header `X-Family-Member`) is the caller for chat, purchases, approve and reject. A `memberName` in the body
  cannot override it (403). A missing header gives 401. Only a parent may change the model provider.
- A stored API key is kept only while the provider and base URL stay the same, so it is never sent to a new host.
  Private and link-local base URLs are refused.
- The catalogue is the live idealo MCP when the idealo sign-in is connected and a model key is set. Otherwise the sample catalogue is used.
- `src/cli.js` (`npm start`) is an older CLI that still uses a local JSON budget and does not go through the wallet.
- Budget-aware offers: the wallet decides per offer (`check_budget(price_cents)` gives `fits`) for the signed-in member. The assistant lists
  only offers that fit and otherwise says what is left. The live idealo catalogue and mock search results (no price) are not filtered.
- `/api/state` and the chat context are read as the signed-in member: teen and child see only their own orders, requests and budget, plus the family totals.
- Demo links: `?as=parent|teen|child` signs in as that member and `?q=<text>` fills the chat, e.g. `http://localhost:6274/?as=child&q=headphones`.
- The sample catalogue has 13 products with invented shops, prices and 30 day histories (`_meta.source` says so).
- Smoke tests with the server running: `node scripts/ui_wallet_smoke.mjs` (62 of 62 with `FAKE_LLM=1` and `scripts/fake_llm.mjs` running, last run 2026-11-27 evening) and
  `node scripts/offline_agent_budget_check.mjs` (10 of 10). Provider path against a local fake server: `node scripts/fake_llm.mjs`, then
  `FAKE_LLM=1 node scripts/ui_wallet_smoke.mjs` (62 of 62).
- No automated test covers a real OpenAI or Nebius key, the live idealo sign-in or the `ALLOW_UNVERIFIED_LIVE_PURCHASES` path.
  The owner reports the live idealo MCP and an own model key working in the app (2026-11-27).

## For the team: first-time GitHub setup (from your clone)
```bash
brew install gh                      # if missing
gh auth login                        # if not logged in as mikomeller
gh auth refresh -s project           # Projects scope
python3 scripts/setup_github.py --dry-run   # check, no network
python3 scripts/setup_github.py             # creates repo, labels, milestones, Project, fields, 40 issues (7 epics), epic links
```
The script creates the repo `mikomeller/12_family_shopper_agent` (now public), makes the first commit and pushes.
It is safe to re-run. If your Project already has another number, pass `--project-number <N>`.

Then, once, in the Project: **New view → Board → Column by: Stage**. Under **Workflows** enable
**Auto-add to project** for this repo so new issues land on the board.

## Branches
`main` is reserved for reviewed code and only changes through pull requests.
Every collaborator gets a branch named after their GitHub login, started from `main`:
```bash
python3 scripts/create_collaborator_branches.py --dry-run   # shows who gets which branch
python3 scripts/create_collaborator_branches.py
```
Covers accepted collaborators and pending invitations (owner skipped). Re-run after inviting new people.

## For the team: Boris setup
Docker running · `brew install --cask affinidi-ai/tap/boris` · `boris doctor` ·
`boris login --url https://trustboris.ai` · use Chrome (not Safari). See milestone **M0 Pre-kickoff**.
