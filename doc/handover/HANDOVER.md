<!--
Author:    mikomeller
Version:   0.1.1
Filename:  HANDOVER.md
Pathname:  doc/handover/HANDOVER.md
Purpose:   Handover for whoever continues 12_family_shopper_agent (person or Claude Code session):
           current state, decisions, how to start, risks and what is unverified
-->
# Handover — 12_family_shopper_agent (2026-11-27)

## Start here
```bash
cd ~/Documents/M1_20230921/src/genAI/12_family_shopper_agent
python3 scripts/setup_github.py --dry-run     # check: 40 issues, 30 epic links
python3 scripts/setup_github.py               # adds 7 epics + 10 stories, links stories to epics
python3 scripts/board.py list --stage Ready   # the board in the terminal
mkdir -p .claude/agents && cp doc/agents/*.md .claude/agents/   # install the agent definitions (once, and after every change)
claude --agent orchestrator                   # orchestrator session with Opus/Sonnet subagents
```
Next steps with owners: [`doc/tasks/pending.md`](../tasks/pending.md).

## What this project is
A family shopping agent for the Affinidi TrustBoris hackathon. It searches the read-only idealo MCP and orders
through our own Family Wallet MCP, which enforces personal and family monthly caps. See `README.md`,
`doc/research/affinidi_boris_idealo.md` and `doc/diagrams/`.

## State
| Area | State |
|---|---|
| Repo, labels, milestones, Project, 23 issues | done (confirmed by the owner 2026-11-27) |
| Epic → Story structure (7 epics, 10 new stories, sub-issue links) | in `backlog.json` v0.1.2; script run on GitHub pending |
| Orchestrator + 5 subagents (source `doc/agents/`) | written; not yet installed to `.claude/agents/` or run in Claude Code |
| Board access from the terminal (`scripts/board.py`) | written; tested against a stub only |
| Eval plan (`doc/evals/eval_plan.md`) | written; no eval code yet |
| Product code (wallet, idealo mock, eval harness) | not started |
| Boris: account, CLI, identity spike | not started (human) |

## How the orchestration works
Diagram: [`doc/diagrams/orchestration.mmd`](../diagrams/orchestration.mmd).

| Agent | Model | Job | May write |
|---|---|---|---|
| `orchestrator` | session model (`inherit`) | plan from the board, delegate, run gates, keep handover current | plans, handover, small fixes |
| `architect` | Opus | contracts, data model, diagrams, ADRs | `doc/design/`, `doc/diagrams/` |
| `reviewer` | Opus | independent read-only review | nothing |
| `wallet-dev` | Sonnet | Python implementation from an approved design | code, config |
| `test-eval` | Sonnet | tests, eval harness, scenarios, results | `tests/`, `evals/` |
| `docs-demo` | Sonnet | runbooks, demo script, pitch | `doc/`, `README.md` |

The agent files are kept in `doc/agents/` and copied to `.claude/agents/`, because the Claude desktop app may not
write into `.claude`. Edit the source in `doc/agents/`, then copy again.
The orchestrator's system prompt is the body of `orchestrator.md`; `claude --agent orchestrator`
makes it the main session. To make it the default, add `{"agent": "orchestrator"}` to `.claude/settings.json`.

## Decisions
| Decision | Reason |
|---|---|
| Epic = parent issue (`type:epic`), Story = sub-issue, Task = checkbox | hierarchy without 80+ issues |
| Re-running `setup_github.py` sets board fields only on new issues | a re-run must not move cards the team moved |
| Stack: Python 3.12, uv, MCP Python SDK, SQLite, Pydantic, pytest, ruff, Docker Compose | open source, minimal; ADR story in E6 |
| Money in integer cents; cap check + order in one write transaction | no rounding errors, no double spend |
| Identity through one resolver interface | the Boris identity spike then changes one module |
| Offline idealo mock for development and evals | idealo trial allows 500 calls/day |
| The wallet enforces role rules itself, in addition to Boris gating | still safe when Boris is off |
| Opus designs and reviews, Sonnet builds | review stays independent of the builder |

## Open decisions (for the owner)
- A1: does a parent-approved child order count against the child's cap? Assumed yes.
- A2: L3 eval pass marks (3 of 3 safety, 2 of 3 task).
- Hackathon date and team size are not known here; they decide whether E4 (evals) and CI stay in scope.

## Unverified — check before relying on it
- GitHub sub-issue linking on a personal account: the script uses `POST /repos/{owner}/{repo}/issues/{n}/sub_issues`
  and reports failures without stopping; failed links can be added by hand in the epic.
- `scripts/board.py` assumes `gh project item-list --format json` prints custom fields as top-level keys (`stage`, `priority`).
- Tool versions (Python, uv, MCP SDK, ruff, pytest) are not pinned yet; check each against its documentation in the dev-environment story.
- Whether Boris forwards the caller identity to MCP tools (spike, P0) and what exactly fails with Boris off.
- The subagent `tools` lists use Claude Code's tool names as documented on 2026-11-27.

## Risks
| Risk | Effect | Mitigation |
|---|---|---|
| Boris does not forward identity | personal caps cannot be applied | resolver with signed member token, or one access point per role |
| idealo quota used up during the demo | search stops | mock server, Boris response cache |
| Agent ignores a cap in conversation | none on money | caps are enforced in the wallet, checked by L1/L2/S-10 |
| Git from the Claude desktop sandbox | lock files left in `.git` | run git only in your own terminal or Claude Code |

## Rules that always apply
`CLAUDE.md` and `doc/tasks/lessons.md`: plan first, diagram before code, header on every file, never delete
without approval, proof before done, `main` only through pull requests.
