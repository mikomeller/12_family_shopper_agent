<!--
Author:    mikomeller
Version:   0.1.1
Filename:  pending.md
Pathname:  doc/tasks/pending.md
Purpose:   Pending tasks and next steps for 12_family_shopper_agent, in order, with owner and proof;
           updated by the orchestrator at the end of every session
-->
# Pending tasks and steps

Owner: **You** = a person at the keyboard · **Orch** = `claude --agent orchestrator` and its subagents.
The board is the source of truth for stories; this file is the order to work in.

## Step 1 — Bring the board up to date (You, about 10 minutes)
- [ ] `python3 scripts/setup_github.py --dry-run` → prints "backlog.json OK: 40 issues, 13 labels, 5 fields"
- [ ] `python3 scripts/setup_github.py` → "issues created: 17, reused: 23" and "linked: 30"
- [ ] If links fail: open each epic → sub-issues menu → "Add existing issue"
- [ ] `python3 scripts/board.py list` → cards grouped by Stage; if columns are empty, report the JSON shape (unverified, see handover)
- [ ] Install the agents: `mkdir -p .claude/agents && cp doc/agents/*.md .claude/agents/`
- [ ] Commit on your branch and open a pull request: `.claude/agents/`, `doc/`, `scripts/`, `CLAUDE.md`, `README.md`
- [ ] Decide A1 (approved child order counts against the child's cap?) and A2 (eval pass marks)

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
- [ ] Dev environment: diagram, `pyproject.toml`, `uv.lock`, ruff, pytest, Docker Compose (wallet-dev)
- [ ] CI workflow: ruff + pytest on pull requests (wallet-dev, P2)

## Step 5 — Family Wallet MCP, Epic E1 (Orch)
- [ ] Design the tool contract `doc/design/wallet_mcp.md` + diagrams + role/tool matrix (architect)
- [ ] Pluggable identity resolver (wallet-dev; final resolver after the spike)
- [ ] Implement the wallet server (wallet-dev)
- [ ] Cap tests L1-01…L1-13 and contract tests L2-01…L2-09 (test-eval) → 100%
- [ ] Seed and reset script (wallet-dev)
- [ ] Review (reviewer) → approve

## Step 6 — Agent and evals, Epics E2 + E4 (Orch, then You for Boris)
- [ ] idealo mock MCP server with fixtures, one containing an injection (wallet-dev)
- [ ] Eval harness for YAML scenarios (test-eval)
- [ ] **You:** create the Family Buyer agent in Boris Agent Builder
- [ ] End-to-end purchase flow against the mock, then live idealo
- [ ] Scenarios S-01…S-10, three runs each (test-eval)

## Step 7 — Trust layer, Epic E3 (You, with runbooks from docs-demo)
- [ ] Caller identity for parent, teen, child · tool gating per role
- [ ] Screening · throttle · response cache · backup model
- [ ] With/without-Boris eval run (L4)

## Step 8 — Demo and pitch, Epic E5 (docs-demo, then You)
- [ ] Demo script with exact prompts · "without Boris" comparison · pitch outline
- [ ] Two full dry runs; bugs logged as issues

## Carried over from earlier tasks
- [ ] Invite collaborators to the repo, then `python3 scripts/create_collaborator_branches.py`
- [ ] Board view "Board", Column by = Stage; enable the Auto-add workflow (if not done)
- [ ] Optional: protect `main` (needs GitHub Pro on a private personal repo)
