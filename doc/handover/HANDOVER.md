<!--
Author:    mikomeller
Version:   0.1.3
Filename:  HANDOVER.md
Pathname:  doc/handover/HANDOVER.md
Purpose:   Handover for whoever continues 12_family_shopper_agent (person or Claude Code session):
           current state, decisions, how to start, risks and what is unverified
-->
# Handover — 12_family_shopper_agent (2026-11-27)

## Start here
Work only in this folder (owner decision 2026-11-27); ask before cloning anywhere else.
```bash
cd ~/Documents/M1_20230921/src/genAI/12_family_shopper_agent
uv sync                                        # install dependencies
uv run pytest -q                               # expected: 144 passed, 13 skipped
uv run python scripts/demo.py                  # offline demo, ends: DEMO OK: 5/5 scenes
mkdir -p .claude/agents && cp doc/agents/*.md .claude/agents/   # install the agent definitions (once, and after every change)
claude --agent orchestrator                    # orchestrator session with Opus/Sonnet subagents
```
Start servers with `PYTHONPATH=src uv run python -m ...` (macOS hidden-flag problem with the editable install).
Next steps with owners: [`doc/tasks/pending.md`](../tasks/pending.md).

## What this project is
A family shopping agent for the Affinidi TrustBoris hackathon. It searches the read-only idealo MCP and orders
through our own Family Wallet MCP, which enforces personal and family monthly caps. See `README.md`,
`doc/research/affinidi_boris_idealo.md` and `doc/diagrams/`.

## State
| Area | State |
|---|---|
| Repo (public), labels, milestones, Project, issues | done; `setup_github.py` run live: 7 epics + 10 stories, 30 links, 0 failures; later E7 (#45), #46-#48 and new stories #51-#55 (linked to their epics); `backlog.json` v0.1.4 (49 issues); ticket #25 under Epic #45 with the design assessment as comment |
| CI `.github/workflows/ci.yml` + automerge (label `automerge`, squash) | done; verified live on PR #44 (0c6de28), PR #49 (55513dc), #50 and #56 (merge commit fe056fb); `main` has no branch protection |
| Wallet design, server (8 tools: new `reject_request`, parent only; status `rejected`; `list_requests` accepts `rejected`; old databases migrated in `init_db`; story #51), seed script | on `main`; seed script has no guard before wiping the db |
| Cap and contract tests L1 + L2 | 72 of 72 pass (`evals/results/2026-11-27_l1_l2.md`); full suite `uv run pytest -q` 144 passed, 13 skipped; `uv run ruff check .` clean |
| idealo mock + fixtures (one injection) | on `main`; real idealo response shapes unverified |
| Discount check (`check_discount`, Epic E7, ticket #25) | designed and built; DC-01…DC-19 pass; corrected design `doc/design/discount_check.md` |
| Offline demo `scripts/demo.py`, `doc/demo/demo_script.md` | `DEMO OK: 5/5 scenes`; demo script has a browser variant (not yet tried by anyone) |
| Boris system prompt and runbooks | written; every Boris dashboard step unverified |
| Boris CLI in Docker (`docker/boris/`) | CLI 0.1.35 runs; image now contains the Docker client, `boris doctor` shows Docker OK; `boris login` not done (owner); the boris service mounts `/var/run/docker.sock` |
| Web UI (collaborator PR #33, Node/React, OpenAI) | merged; wallet-wired; simulated family accounts (account switcher Parent / Teen / Child, header `X-Family-Member`, 403 on a mismatching `memberName`, 401 without header); offline chat mode without `OPENAI_API_KEY` (`mode: "offline-mock"`); INFLATED blocks in the purchase path; `node scripts/ui_wallet_smoke.mjs` 17 of 17 (also via Docker); not tested: chat with a real OpenAI key, live idealo OAuth, UI in a browser; `src/cli.js` (`npm start`) still uses its own float budget file and bypasses the wallet (story #53) |
| Full application in Docker (story #54) | `docker compose up -d --build app` serves `http://localhost:6274`; wallet db in volume `app-data`; runbook `doc/runbooks/docker_app.md`; container currently running on the owner's Mac |
| Eval harness (stories #37-#39) | `evals/harness.py`, `drivers.py`, scenarios S-01...S-13, `test_l3_scenarios.py`, `test_l4_gating.py`, `run_report.py`; scripted and adversarial driver at the tool layer: task 3/3, safety 3/3 (`evals/results/2026-11-27_l3_l4.md`); L4 is a SIMULATION of Boris gating; 13 tests skip without an LLM key, LLM driver is a stub |
| Orchestrator + 5 subagents (source `doc/agents/`) | written and installed |
| Independent review | earlier round: approve, no blocking findings; PR #56: review pending (merged first because of the deadline) |
| Not done | Boris agent in Agent Builder, Boris login, identity spike #4, idealo live smoke test #3, L3/L4 with an LLM agent and Boris, ADR 0001, OpenAI key / idealo sign-in / Boris connection details from the owner (#55) |

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
| 2026-11-27 owner: orchestrator may push, open PRs, label them `automerge`, squash only | CI must be green; never push to `main` directly, never force-push |
| 2026-11-27 owner: development only in the allowed folder | no second clones |
| 2026-11-27 owner: A1 confirmed (approved child order counts against child's personal cap and family cap) | cap rules |
| 2026-11-27 owner: A2 confirmed (safety scenarios 3 of 3) | L3 pass marks |
| One wallet access point per role: member from `WALLET_MEMBER_TOKEN` (HMAC-SHA256, secret `WALLET_TOKEN_SECRET`) per server process | until spike #4 shows whether Boris forwards identity |
| Discount check as Python module + MCP tool on the idealo mock; Node/TS service rejected | ticket #25 formula was not sound; INFLATED warns, does not block (proposal; superseded by the owner decision below) |
| 2026-11-27 owner: a parent can reject a request | tool `reject_request`; a rejected request never becomes an order (story #51) |
| 2026-11-27 owner: an INFLATED discount BLOCKS the order | enforced in the web UI server purchase path and in system prompt rule 8; the wallet cannot verify a discount (no price history), so a misbehaving agent is limited only by the caps (story #52) |
| 2026-11-27: web UI family accounts are a demo sign-in | production identity must come from TrustBoris (story #53) |
| Questions to the owner are numbered points | owner preference |

## Open decisions (for the owner)
- Where `sale_days` for the discount check comes from.
- Decided 2026-11-27: a parent can reject a request; INFLATED blocks the order (see Decisions).
- Review of collaborator PR #33 (superseded if the wallet-wired version is merged); whether to comment on ticket #25.
- Decided 2026-11-27: A1, A2 (see Decisions).

## Unverified — check before relying on it
- GitHub sub-issue linking on a personal account: the script uses `POST /repos/{owner}/{repo}/issues/{n}/sub_issues`
  and reports failures without stopping; failed links can be added by hand in the epic.
- `scripts/board.py` assumes `gh project item-list --format json` prints custom fields as top-level keys (`stage`, `priority`).
- Tool versions (Python, uv, MCP SDK, ruff, pytest) are not pinned yet; check each against its documentation in the dev-environment story.
- Whether Boris forwards the caller identity to MCP tools (spike, P0) and what exactly fails with Boris off.
- Every Boris dashboard step in `doc/runbooks/boris_agent_setup.md`; the Boris login (`--device`); commands that host agents need the docker CLI in the image (not done).
- What idealo's real responses and price history contain (the mock shapes are guesses).
- Web UI: the chat endpoint with a real OpenAI key and idealo OAuth; the UI clicked through in a browser.
- L3/L4 with an LLM agent or TrustBoris (LLM driver is a stub; L4 is a simulation).
- The result of the independent review of PR #56 (pending).
- Boris connection details, OpenAI key and idealo sign-in: checked today, branch `rodrigo-agent` and PR #33 contain none of them (`.env.example` has an empty key; idealo tokens are in the git-ignored `.data/idealo-oauth.json` on the machine that signed in). Asked from the owner in #55; secrets must never be pushed to this public repo.
- The subagent `tools` lists use Claude Code's tool names as documented on 2026-11-27.

## Risks
| Risk | Effect | Mitigation |
|---|---|---|
| Boris does not forward identity | personal caps cannot be applied | resolver with signed member token, or one access point per role |
| idealo quota used up during the demo | search stops | mock server, Boris response cache |
| Agent ignores a cap in conversation | none on money | caps are enforced in the wallet, checked by L1/L2/S-10 |
| Auto-merge without human review on an unprotected public `main` | a green but wrong PR lands on `main` | tests and reviewer before labeling; consider branch protection |
| Web UI depends on an OpenAI key and sends family budget data to OpenAI | data leaves the project; key handling | keep the key out of the repo; decide whether this is acceptable for the demo |
| Demo sign-in header `X-Family-Member` is not authentication | anyone who can reach the port can act as any member | demo only; production identity from TrustBoris |
| `boris` service mounts `/var/run/docker.sock` | that container controls the host's Docker; weakens isolation | use only on request, only that service |
| The Docker app serves the Vite dev server | not a production build | demo use only |
| Wallet cannot stop an injected quantity (eval finding: a misbehaving teen agent buys 2 backpacks within the 50 EUR cap) | spend up to the caps | only the caps limit it; system prompt rules |
| Git from the Claude desktop sandbox | lock files left in `.git` | run git only in your own terminal or Claude Code |

## Rules that always apply
`CLAUDE.md` and `doc/tasks/lessons.md`: plan first, diagram before code, header on every file, never delete
without approval, proof before done, `main` only through pull requests.
