<!--
Author:    mikomeller
Version:   0.1.3
Filename:  pending.md
Pathname:  doc/tasks/pending.md
Purpose:   Pending tasks and next steps for 12_family_shopper_agent, in order, with owner and proof;
           updated by the orchestrator at the end of every session
-->
# Pending tasks and steps

Owner: **You** = a person at the keyboard · **Orch** = `claude --agent orchestrator` and its subagents.
The board is the source of truth for stories; this file is the order to work in.

## Next, in order (updated 2026-11-27 evening)
1. (You) Supply the OpenAI key, the idealo sign-in and the Boris connection details (#55). They are in no branch and must never be pushed to this public repo.
2. (You) `boris login` in the container (`--device`) and create the agent in Agent Builder per `doc/runbooks/boris_agent_setup.md`.
3. (You) Spike #4: does Boris forward the caller identity?
4. (Orch) Implement the LLM driver in `evals/drivers.py`, run L3 for real (`uv run pytest -q evals -m "l3 or l4"`), then L4 against Boris.
5. (Orch) Fix the reviewer's findings for PR #56 (review pending; PR was merged first because of the deadline). Older remarks: seed script guard before it wipes the db; `personal_cap: null` not forbidden for teen/child; `deep_link` scheme not restricted; `list_orders("2026-13")` accepted; mock `check_discount` coerces with int(); token expiry parsing accepts `+`/`_` (harmless).
6. (Orch) Rewire `src/cli.js` (`npm start`) to the wallet or remove it (removal needs the owner's go).
Also open: source of `sale_days` (owner); try the UI in a browser (You).

## Questions to the owner
1. OpenAI key into `.env` (repo root, git-ignored)?
2. idealo: copy `.data/idealo-oauth.json` from the machine that signed in, or click "Connect idealo" in the UI?
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

## Carried over from earlier tasks
- [ ] Invite collaborators to the repo, then `python3 scripts/create_collaborator_branches.py`
- [ ] Board view "Board", Column by = Stage; enable the Auto-add workflow (if not done)
- [ ] Optional: protect `main` (needs GitHub Pro on a private personal repo)
