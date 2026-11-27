<!--
Author:    mikomeller
Version:   0.1.5
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
`npm start` runs the older CLI, which still uses a local JSON budget and does not go through the wallet.
Smoke test with the server running: `node scripts/ui_wallet_smoke.mjs`.

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
