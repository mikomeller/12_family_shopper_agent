<!--
Author:    mikomeller
Version:   0.1.4
Filename:  README.md
Pathname:  README.md
Purpose:   Overview, structure and first-time setup of 12_family_shopper_agent
-->
# 12_family_shopper_agent

A family shopping agent project originally explored with Affinidi **TrustBoris** for the AI Agents Berlin hackathon (Affinidi challenge).
This branch adds a runnable local React app that searches and compares products through the official **idealo MCP**.
Its purchases are simulated only: the app records a mock purchase against a local demo budget and cannot place real orders.

The role model below is part of the longer-term concept; it is not implemented by the local browser demo.

| Role | Proposed permissions | Example monthly cap |
|---|---|---|
| Parent | everything, approves requests, sets budgets | none (family cap applies) |
| Teen | search and order alone | €50 |
| Child | search; every order becomes an approval request | €20 |
| Family | all orders together | €400 |

## Run the local browser demo

Requirements: Node.js 20 or newer, plus an OpenAI API key for assistant responses.

From the repository folder, install the dependencies and create local settings and sample family data:

```bash
npm install
cp .env.example .env
cp data/family.example.json data/family.json
```

Add your OpenAI API key to `OPENAI_API_KEY` in `.env`. Keep `.env` private; it is ignored by Git. Then start both the local server and the React app:

```bash
npm run dev
```

Open [http://localhost:6274](http://localhost:6274). Stop the app with **Ctrl+C** in the terminal.

## Connect idealo

1. With the app running, click **Connect idealo**.
2. Sign in to idealo in the authorization page and approve access.
3. Return to Family Shopper. It reports **idealo tools ready** after it confirms access to the MCP tools.

The app uses OAuth through idealo MCP. You do not need an idealo API key or a manually copied token. Keep the development app on `http://localhost:6274` during sign-in; the callback address is:

```text
http://localhost:6274/oauth/callback
```

The Vite development server forwards the OAuth callback to the local app server on port `3001`. OAuth details are stored in `.data/idealo-oauth.json`, which is ignored by Git. Do not share this file or its tokens.

If you see **Invalid redirect URI**, check that you are using the local address and port above. If idealo returns **403 Forbidden**, click **Reconnect idealo** to register and authorize a fresh Family Shopper OAuth client. Codex and Family Shopper use separate OAuth clients. If the fresh check still returns 403, contact idealo MCP support and ask them to inspect the Family Shopper client's MCP request.

## Family budgets and mock purchases

Sample profiles are in `data/family.example.json`. Copy it to `data/family.json` for a local starting point, then edit the names and `spendingLimitEur` values or use the **+** button beside **Budget overview** in the app. Local profiles and purchase history are stored in `data/family.json`, which is ignored by Git.

Product requests use each person's remaining demo budget. For the same product, the assistant compares idealo shops by total price, including shipping when known, and highlights the cheapest listed option. Clicking **Buy (mock)** in an offer table records that offer's listed price in the local ledger and updates the demo budget. It does not open a shop checkout, take payment, or place an order.

The app reads its shopping instructions from `skills/family-shopper/SKILL.md`. The skill guides the assistant; the React app and local server load it and perform the MCP calls.

## Configuration and data

`.env.example` lists the available settings:

| Setting | Purpose | Default |
| --- | --- | --- |
| `OPENAI_API_KEY` | Key used by the local server for assistant responses | Required |
| `OPENAI_MODEL` | OpenAI Responses API model | `gpt-6.2-sol` |
| `IDEALO_MCP_URL` | idealo MCP endpoint | `https://mcp.idealo.com/mcp` |

Chat requests, shopping instructions, and family budget information are sent to the OpenAI API; product searches are made through idealo MCP. The browser app uses a local server so the OpenAI API key stays out of the browser. This demo runs locally for one user and does not have accounts or access controls for family sharing.

Architecture: [`doc/diagrams/family_buyer_architecture.mmd`](doc/diagrams/family_buyer_architecture.mmd) ·
Purchase flow: [`doc/diagrams/purchase_decision_sequence.mmd`](doc/diagrams/purchase_decision_sequence.mmd) ·
Research: [`doc/research/affinidi_boris_idealo.md`](doc/research/affinidi_boris_idealo.md)

## Structure
```
.github/ISSUE_TEMPLATE/   Idea, Task, Bug issue forms
config/                   family_budget.example.yaml (copy to family_budget.yaml)
doc/research/             research and spike results
doc/diagrams/             Mermaid diagrams (before code)
doc/agents/               orchestrator + subagents for Claude Code; copy to .claude/agents/, then: claude --agent orchestrator
doc/evals/                eval_plan.md (gates, eval levels, scenarios)
doc/handover/             HANDOVER.md (state, decisions, how to start)
doc/tasks/                todo.md (plan), pending.md (next steps) and lessons.md
scripts/                  setup_github.py + backlog.json, board.py (board in the terminal)
```

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
