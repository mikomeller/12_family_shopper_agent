<!--
Author:    mikomeller
Version:   0.1.4
Filename:  pending.md
Pathname:  doc/tasks/pending.md
Purpose:   Pending tasks and next steps for 12_family_shopper_agent, in order, with owner and proof;
           updated by the orchestrator at the end of every session
-->
# Pending tasks and steps

Owner: **You** = a person at the keyboard · **Orch** = `claude --agent orchestrator` and its subagents.
The board is the source of truth for stories; this file is the order to work in.

## Next, in order (updated 2026-11-27 late evening)
1. (You) Issue #55, numbered: 1. OpenAI or Nebius key: enter it in the "Model provider" dialog or `.env` (never commit it). 2. idealo: sign in with "Connect idealo" (live-catalogue purchases are refused for now). 3. Boris connection details.
2. (You) `boris login` in the container (`--device`) and create the agent in Agent Builder per `doc/runbooks/boris_agent_setup.md`.
3. (You) Spike #4: does Boris forward the caller identity?
4. (Orch) Implement the LLM driver in `evals/drivers.py`, run L3 for real (`uv run pytest -q evals -m "l3 or l4"`), then L4 against Boris.
5. (Orch) Live idealo verification (smoke test #3) so live-catalogue purchases can be enabled (now refused with 501).
6. (Orch) Open reviewer remarks (non-blocking): `GET /api/llm` readable by every member; teen and child see family-wide totals; `get_product_details` / `get_product_price_history` not budget-filtered; token TTL of 1 day never refreshed by the Node server; migration re-reads schema outside the transaction; `uv:latest` unpinned in the app image; seed script guard before it wipes the db. Older remarks: `personal_cap: null` not forbidden for teen/child; `deep_link` scheme not restricted; `list_orders("2026-13")` accepted; mock `check_discount` coerces with int().
7. (Orch) Rewire `src/cli.js` (`npm start`) to the wallet or remove it (removal needs the owner's go).
8. (You) A real browser click-through of the UI (nobody has done it); scenario S-14 into the eval harness.
Also open: source of `sale_days` (owner).

## Proven today (2026-11-27 late evening)
- [x] Independent review of PR #59: approve, nothing blocking; PR #59 merged (a31a110), CI green. The blocking findings B1 and B2 of the PR #56 review are fixed and were re-attacked.
- [x] Budget-aware offers: `node scripts/offline_agent_budget_check.mjs` 6 of 6
- [x] Provider path against a local fake server: `FAKE_LLM=1 node scripts/ui_wallet_smoke.mjs` 43 of 43 (NOT a real OpenAI or Nebius key)
- [x] Docker rebuilt, offline smoke 32 of 32 through `http://localhost:6274`
- [x] `uv run pytest -q` 152 passed, 13 skipped; ruff clean; `scripts/demo.py` 5/5
- [ ] Not proven: a real OpenAI key, a real Nebius key, live idealo OAuth, browser click-through, `ALLOW_UNVERIFIED_LIVE_PURCHASES` path

## Questions to the owner
1. OpenAI or Nebius key: enter it in the "Model provider" dialog or `.env` (repo root, git-ignored)?
2. idealo: copy `.data/idealo-oauth.json` from the machine that signed in, or click "Connect idealo" in the UI (live-catalogue purchases are refused for now)?
3. Where are the Boris connection details?

Decided 2026-11-27: a parent can reject a request; INFLATED blocks the order.

## Step 1 — Bring the board up to date (You, about 10 minutes)
- [x] `python3 scripts/setup_github.py --dry-run` → prints "backlog.json OK: 40 issues, 13 labels, 5 fields" (backlog.json is now v0.1.3, 44 issues)
- [x] `python3 scripts/setup_github.py` → run live: 7 epics + 10 stories created, 30 stories linked, 0 failures
- [ ] If links fail: open each epic → sub-issues menu → "Add existing issue"
- [ ] `python3 scripts/board.py list` → cards grouped by Stage; if columns are empty, report the JSON shape (unverified, see handover)
- [x] Install the agents: `mkdir -p .claude/agents && cp doc/agents/*.md .claude/agents/` (done: `.claude/agents/` is read in this session)
- [ ] Commit on your branch and open a pull request: `.claude/agents/`, `doc/`, `scripts/`, `CLAUDE.md`, `README.md`
- [x] Decide A1 and A2: both confirmed by the owner 2026-11-27

## Step 2 — First orchestrator session (You + Orch)
- [ ] `claude --agent orchestrator` starts; ask "which subagents do you have?" → five listed
- [ ] Ask "what is next?" → it reads the board and proposes a Ready story
- [ ] Tick the story "Orchestrator and subagent definitions for Claude Code" when one story has passed all gates

## Step 3 — Pre-kickoff, Epic E0 (You; Orch writes the runbooks)
- [ ] Create TrustBoris account and team access
- [ ] Install and verify the Boris CLI (`boris doctor`)
- [ ] Connect idealo MCP, smoke-test the four tools, save response shapes to `doc/research/idealo_samples.md`
- [ ] **Spike (P0):** does Boris forward the caller identity to MCP tools? → `doc/research/boris_identity_spike.md`
- [ ] Optional: request the idealo partner tier

## Step 4 — Foundation, Epic E6 (Orch)
- [ ] Stack decision record `doc/design/adr_0001_stack.md` (architect → reviewer)
- [ ] Dev environment: diagram, `pyproject.toml`, `uv.lock`, ruff, pytest (wallet-dev); [x] Docker Compose app (`compose.yaml`, `doc/runbooks/docker_app.md`)
- [x] CI workflow: ruff + pytest on pull requests, automerge (verified on PR #44, #49, #50, #56)

## Step 5 — Family Wallet MCP, Epic E1 (Orch)
- [x] Design the tool contract `doc/design/wallet_mcp.md` + diagrams + role/tool matrix (architect)
- [x] Pluggable identity resolver (wallet-dev; token from `WALLET_MEMBER_TOKEN`; final resolver after the spike)
- [x] Implement the wallet server (wallet-dev): 8 tools (`reject_request` added, story #51)
- [x] Cap tests L1-01…L1-13 and contract tests L2-01…L2-09 (test-eval) → 72 of 72
- [x] Seed and reset script (wallet-dev): `scripts/seed_wallet.py`; guard still to add
- [x] Review (reviewer) → approve, no blocking findings

## Step 6 — Agent and evals, Epics E2 + E4 (Orch, then You for Boris)
- [x] idealo mock MCP server with fixtures, one containing an injection (wallet-dev)
- [x] Eval harness for YAML scenarios (test-eval): `evals/harness.py`, scenarios S-01...S-13; run with scripted and adversarial driver, LLM driver is a stub
- [ ] **You:** create the Family Buyer agent in Boris Agent Builder
- [ ] End-to-end purchase flow against the mock, then live idealo
- [x] Scenarios S-01…S-13 at the tool layer: task 3/3, safety 3/3 with both drivers; [ ] same with an LLM agent (skipped without key)

## Step 7 — Trust layer, Epic E3 (You, with runbooks from docs-demo)
- [ ] Caller identity for parent, teen, child · tool gating per role
- [ ] Screening · throttle · response cache · backup model
- [x] L4 gating as a SIMULATION (`evals/test_l4_gating.py`); [ ] real L4 against Boris

## Step 8 — Demo and pitch, Epic E5 (docs-demo, then You)
- [x] Demo script with exact prompts (`doc/demo/demo_script.md`) · [ ] "without Boris" comparison · [ ] pitch outline
- [ ] Two full dry runs (browser click-through not yet tried by anyone); bugs logged as issues
- [x] Browser demo variant with `?as=` / `?q=` links written (`doc/demo/demo_script.md`); not yet clicked through

## Carried over from earlier tasks
- [ ] Invite collaborators to the repo, then `python3 scripts/create_collaborator_branches.py`
- [ ] Board view "Board", Column by = Stage; enable the Auto-add workflow (if not done)
- [ ] Optional: protect `main` (needs GitHub Pro on a private personal repo)
