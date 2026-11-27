<!--
Author:    mikomeller
Version:   0.1.9
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
uv run pytest -q                               # expected: 191 passed, 16 skipped
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
| Cap and contract tests L1 + L2 | 71 of 71 pass (rerun 2026-11-27 evening; report `evals/results/2026-11-27_l1_l2.md` may be older); full suite `uv run pytest -q` 191 passed, 16 skipped; `uv run ruff check .` clean |
| idealo mock + fixtures | on `main`; 13 products (was 4), fictional shops, valid-check-digit EANs, 30-day histories, one product per discount verdict, two injection texts; data INVENTED; real idealo response shapes and prices unverified |
| Discount check (`check_discount`, Epic E7, ticket #25) | designed and built; DC-01…DC-19 pass; corrected design `doc/design/discount_check.md` |
| Offline demo `scripts/demo.py`, `doc/demo/demo_script.md` | `DEMO OK: 5/5 scenes`; demo script has a browser variant (not yet tried by anyone) |
| Boris system prompt and runbooks | written; every Boris dashboard step unverified |
| Boris CLI in Docker (`docker/boris/`) | CLI 0.1.35 runs; image now contains the Docker client, `boris doctor` shows Docker OK; `boris login` not done (owner); the boris service mounts `/var/run/docker.sock` |
| Web UI (collaborator PR #33, Node/React, OpenAI) | merged; wallet-wired; simulated family accounts (account switcher Parent / Teen / Child, header `X-Family-Member`, 403 on a mismatching `memberName`, 401 without header); offline chat mode without `OPENAI_API_KEY` (`mode: "offline-mock"`); INFLATED blocks in the purchase path; `node scripts/ui_wallet_smoke.mjs` 32 offline steps, 32 of 32 via Docker; redesigned (role switcher, offer cards, status cards, budgets panel, dark theme, `?as=` / `?q=` demo links); `/api/state` and chat context are read as the signed-in member; not tested: a real OpenAI or Nebius key, live idealo OAuth, UI clicked through in a browser (only headless screenshots at 1280px); `src/cli.js` (`npm start`) still uses its own float budget file and bypasses the wallet (story #53) |
| Full application in Docker (story #54) | `docker compose up -d --build app` serves `http://localhost:6274` (published on `127.0.0.1` only; rebuilt, offline smoke 32 of 32); wallet db in volume `app-data`; runbook `doc/runbooks/docker_app.md`; container currently running on the owner's Mac |
| Eval harness (stories #37-#39) | `evals/harness.py`, `drivers.py`, scenarios S-01...S-13, S-15, S-16, S-17 (16 files, 3 runs each, all pass), `test_l3_scenarios.py`, `test_l4_gating.py`, `run_report.py`; scripted and adversarial driver at the tool layer: task 3/3, safety 3/3 (`evals/results/2026-11-27_l3_l4.md`); L4 is a SIMULATION of Boris gating; 13 tests skip without an LLM key, LLM driver is a stub |
| Orchestrator + 5 subagents (source `doc/agents/`) | written and installed |
| Independent review | earlier round: approve; PR #56 (merged before review): "changes required", two blocking findings in the web UI purchase path (B1 discount check failed open, B2 client named the price); both fixed in PR #59 and re-attacked by the reviewer: approve, nothing blocking; PR #59 merged by auto-merge, CI green, merge commit a31a110 |
| Budget-aware offers (owner's bug "earphones for 299 € with a 20 € limit") | wallet decides per offer (`check_budget(price_cents)` → `fits`); offline assistant lists only fitting offers; LLM tool path filters `get_product_offers` (`enforceBudget`, fails closed); `node scripts/offline_agent_budget_check.mjs` 6 of 6; limits: mock search results carry no price, live catalogue not filtered, alternatives are only affordable items |
| Server-verified purchases | mock catalogue: known `productRef` needed; price, shop, link, name and was-price from the catalogue; differing client price refused (409); only GENUINE and NOT_BEST_PRICE proceed; live catalogue purchases refused (501) unless `ALLOW_UNVERIFIED_LIVE_PURCHASES=1` (unverified path) |
| Bring your own model provider (story #58) | `src/llm-provider.js` + parent-only "Model provider" dialog: OpenAI / Codex API key, Nebius Token Factory, any OpenAI-compatible endpoint; key in server memory only; tested only against `scripts/fake_llm.mjs`: `FAKE_LLM=1 node scripts/ui_wallet_smoke.mjs` 43 of 43; ChatGPT/Codex subscription OAuth not built |
| Pitch deck `pitch/` (owner) | added by the owner, commit 0f82ed1, merged with PR #59; not edited by the agents; `pitch/*.py` exempt from the line-length lint rule |
| Demo wallet reset and story flow (PR #73, PR #74, merge commit b92ae10; independent review: approve, CI green) | `POST /api/demo/reset`: only with `ALLOW_DEMO_RESET=1` (set for the demo container in `compose.yaml`, off by default: 404), parent only (403), body `{"confirm":"reset-demo-wallet"}` (400); runs `scripts/reset_demo_wallet.py`, one transaction deletes all orders and approval requests and restores the caps 400/50/20; db file, members, tokens stay; not a chat tool. Story UI: "now" banner, three collapsible cases, "Story finished" summary, "Play again" with a confirmation dialog. `scripts/story_replay.mjs` replays the story in headless Chrome (exit 0 only when "Story finished" appears). Verified: pytest 191 passed, 16 skipped; ruff clean; `DEMO_RESET=1 FAKE_LLM=1 node scripts/ui_wallet_smoke.mjs` 67 of 67; replay twice on the demo container (clean and used wallet), then three orders, Child 0,00 €, Teen 0,00 €, Family 278,04 € left. Deck `pitch/pitch.html` shows three cases. Demo container runs this build at `http://localhost:6274`, clean wallet |
| Not done | Boris agent in Agent Builder, Boris login, identity spike #4, idealo live smoke test #3, L3/L4 with an LLM agent and Boris, ADR 0001, OpenAI key / idealo sign-in / Boris connection details from the owner (#55) |

## Update 2026-11-27 evening (rhaveen-sa)
- Pitch: `pitch/pitch.html` is the Rings deck (8 main and 2 backup slides); plain fallback `pitch/pitch_plain.html`; 2 minute script `pitch/pitch_script_2min.md`.
- README is a product README (live idealo MCP, own model key). Panel review and scores: `doc/reviews/2026-11-27_pitch_panel_review.md`.
- Design system "Rings": website brief and mockup in `doc/design/website_design.md` and `website_mockup.html`; the web app uses it (`doc/design/app_ui_rings.md`).
- PR #62 (pitch, README, designs) has the `automerge` label. The app restyle is on branch `rhaveen-sa-ui-rings`.

## Update 2026-11-27 late evening (rounds four to seven)
All facts below are verified unless marked.
- **Rule change (owner, 2026-11-27 evening).** Teen (50 EUR) and Child (20 EUR) order on their own up to their monthly budget. Above it the wallet refuses and a parent steps in: the member asks, the parent approves or rejects. A parent-approved order counts against the member's budget and the family budget (400 EUR). Child: PR #69 (route `POST /api/family/request-approval`, chat tool `request_parent_approval`). Teen: PR #70, review pending.
- **Budget-aware offers.** "Within your budget: you can order this yourself." / "Above your budget — a parent can step in" with an Ask-a-parent button.
- **Guided story (PR #63).** `http://localhost:6274/?story=1`, button "Play the story". Real API calls, decision trail; the story's three questions use the deterministic assistant (`scripted: true`). Case 1: Child asks for Der Hobbit, idealo comparison highlights Shop A (10,99 EUR), Child orders, 9,01 EUR left. Case 2: Child asks for a board game (30,98 EUR), refused above the budget, Child asks a parent, Parent approves, family budget pays (358,03 EUR left), child's own budget 0,00 EUR. Case 3 (added 2026-11-27 evening, verified — replayed in headless Chrome on 2026-11-27 evening: 14 steps passed; wallet afterwards: three orders, child 0,00 €, teen 0,00 €, family 278,04 € left): Teen asks for the coffee machine (79,99 EUR, genuine discount, was 99,99 EUR), above the teen's 50 EUR, refused ("This exceeds teen's monthly limit; 50.00 EUR left this month. A parent can step in."), Teen asks a parent, Parent steps in and approves; the order counts against the teen's budget (0,00 EUR left) and the family budget (278,04 € after case 3). The gateway steps in the story are SIMULATED and labelled so: TrustBoris is not connected.
- **Merged to `main` today by auto-merge after CI:** #44, #49, #50, #56, #59, #60, #61, #63, #65 (an EMPTY commit with a misleading title: a text replacement failed unnoticed; fixed properly in #68), #68, #69.
- **Merged by collaborators on their own:** #62 and #64 (rhaveen-sa: pitch deck, README, Rings UI design, light/dark switch), #66 and #67 (c666agent666: `BorisResolver`, takes the caller from the TrustBoris-forwarded identity; OFF by default, enabled with `WALLET_IDENTITY_RESOLVER=boris`; when on it trusts the request `_meta` without a signature check, so it is only safe when the wallet is reachable solely through the Boris gateway).
- **PR #70 MERGED** (teen ask-a-parent path, pitch deck, records) after an independent review (approve), merge commit `907a8fc`. The demo container was rebuilt from that build and the story replayed (wallet afterwards: two child orders, child 0 EUR, family 358,03 EUR).
- **PR #33 (rodrigo-agent) CLOSED** by the owner with a note: its content is on `main` except one commit `fd0fda3` "Expand chat panel dimensions" (7 lines of CSS for the pre-redesign layout), which was not merged.
- **Owner decisions (2026-11-27 evening):** the deck cover chip "Live idealo MCP" stays as it is; no limit on open approval requests per member (not wanted).
- **Rodrigo's four commits merged (#61):** idealo reconnect, 12 tool rounds, confirm dialog before ordering, English replies. UX rework: confirm dialog per role, result notice, state refresh, waiting badge, first-run steps.
- **Real model.** The owner supplied an OpenAI key. It lives ONLY in the git-ignored `.env` on the demo machine. Chat with the real model works against the mock catalogue. The key was pasted in a chat: revoke it after the event. Real-model findings fixed in the web prompt: offer rows need `#ref=`; the model looped when nothing fit.
- **Eval harness:** invariant strengthened (no order above a member's budget without a parent's approval) plus self-check tests.
- **Verified now:** `uv run pytest -q` 191 passed, 16 skipped; ruff clean; `FAKE_LLM=1 node scripts/ui_wallet_smoke.mjs` 62 of 62; `node scripts/offline_agent_budget_check.mjs` 10 of 10; `scripts/demo.py` 5/5; a 30-thread race on the teen's budget never exceeds 50 EUR; the story replayed in headless Chrome against a container (screenshot checked) for the #69 version. Docker endpoint `http://localhost:6274` (127.0.0.1 only) runs the #69 build.
- **Pitch deck, README, handover, lessons updated** for the new rule; `pitch_plain.html` regenerated from `pitch.md` with `uv run --with markdown python pitch/build_html.py`.

### How to run the story
1. `docker compose up -d --build app` (or keep the running container), open `http://localhost:6274/?story=1`.
2. Press "Play the story". Expect the three cases above, a decision trail, and the final family budget (358,03 EUR after case 2; 278,04 € after case 3).
3. Fallback without a browser: `PYTHONPATH=src uv run python scripts/demo.py` ends with `DEMO OK: 5/5 scenes`.
4. Say on stage: TrustBoris is not connected, the gateway steps are simulated, the Family Wallet enforces the limits.

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
| 2026-11-27: the server, not the client, names price and discount | review finding B2; INFLATED and unverifiable discounts blocked; live-catalogue purchases refused until the price can be verified |
| 2026-11-27: the wallet decides whether an offer fits the caller's budget | owner's bug report; every scenario set needs a "what is offered" check per role |
| 2026-11-27: model key held in server memory only, API keys only (no OAuth) | key never leaves the process; private and link-local base URLs refused |
| Questions to the owner are numbered points | owner preference (confirmed 2026-11-27 evening) |
| 2026-11-27 evening owner: Teen and Child order on their own up to their monthly budget (Teen 50 EUR, Child 20 EUR); above it the trust layer refuses and a parent steps in (member asks, parent approves or rejects) | replaces "child: every order is a request" and "teen: over the cap refused" |
| 2026-11-27 evening owner: a parent-approved order counts against the member's budget and the family budget (400 EUR) | cap rules, extends A1 |
| 2026-11-27 owner: Rhaveen stays at write access | admin is impossible on a personally owned repo |
| Guided story uses the deterministic assistant for its two questions | the real model behaved differently from the fake one twice; the story must be repeatable |
| 2026-11-27 owner: the deck demo slide shows three cases; "Play again" resets the wallet itself; keep best practice and a logical flow of information on screen | PR #74 |
| The demo reset is opt-in (`ALLOW_DEMO_RESET=1`), parent only, needs a confirm body, not a chat tool | a reset must never be reachable by the model or by default |
| `BorisResolver` stays OFF by default (`WALLET_IDENTITY_RESOLVER=boris` enables it) | it trusts `_meta` without a signature check: only safe behind the Boris gateway |

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
- Web UI: the chat with a real OpenAI key and a real Nebius key (the Nebius base URL is from its docs page; the default model name is a guess); idealo OAuth; the UI clicked through in a browser (not seen rendered: purchase status cards, approve/reject with a pending request, light theme, 390px phone with data, provider dialog, keyboard focus); the `ALLOW_UNVERIFIED_LIVE_PURCHASES` path; LLM-mode identity under a real model.
- L3/L4 with an LLM agent or TrustBoris (LLM driver is a stub; L4 is a simulation).
- Review result: PR #59 approved, nothing blocking (the review of PR #56 had said changes required; fixed).
- Boris connection details, OpenAI key and idealo sign-in: checked today, branch `rodrigo-agent` and PR #33 contain none of them (`.env.example` has an empty key; idealo tokens are in the git-ignored `.data/idealo-oauth.json` on the machine that signed in). Asked from the owner in #55; secrets must never be pushed to this public repo.
- The subagent `tools` lists use Claude Code's tool names as documented on 2026-11-27.

- Unverified (2026-11-27 late evening): a human click-through of the story and the reset dialog (only a headless-Chrome replay and screenshots); TrustBoris connection (story gateway steps are simulated); live idealo; L3 with a real LLM. Process note: the UI builder subagent ended early with a network error after its edits; its work was verified by the orchestrator (screenshots, browser replay, review), not by its report. Rodrigo's unmerged commit `fd0fda3` (wider chat panel): owner has not decided.
- Unverified (2026-11-27 evening): TrustBoris forwards identity as `BorisResolver` assumes (code merged in #66/#67, never run against Boris); a human click-through of the UI; the real model with the PR #70 teen path; live idealo sign-in.

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
| Open reviewer remarks (non-blocking) | `GET /api/llm` readable by every member (base URL, model, last 4 key characters); teen and child see family-wide totals; `get_product_details` / `get_product_price_history` not budget-filtered (no offers inside); token TTL of 1 day never refreshed by the Node server (after 24 h wallet calls fail until restart); migration re-reads schema outside the transaction; `uv:latest` unpinned in the app image; seed script wipes the db without a guard | fix in the next round; restart the server after 24 h until then |
| Budget filter gaps | mock search results carry no price and the live catalogue is not filtered, so those offers are not filtered; alternatives are only affordable items | the wallet still refuses any order over budget |
| Live purchases refused (501) | the live idealo catalogue cannot be bought through the UI | live idealo verification (#3), then enable |
| Collaborators merge to `main` without review; `main` has no branch protection | an untested or rule-changing PR lands (#62, #64, #67 did) | `git fetch` and merge `origin/main` before every verification run; owner question 3 in `doc/tasks/pending.md` |
| `BorisResolver` trusts `_meta` unsigned when enabled | anyone who reaches the wallet directly can claim a caller | keep it off unless the wallet is reachable only through the Boris gateway |
| A child or teen can create unlimited open requests at any price (reviewer remark) | a parent's queue can be flooded | owner decision 2026-11-27: no limit wanted |
| `GET /api/llm` readable by every member; `/api/idealo/reconnect` needs no sign-in | information and a side effect (writes `.data/idealo-oauth.json`) | acceptable on the 127.0.0.1 bind; not fixed |
| `src/cli.js` (`npm start`) still bypasses the wallet | float budget, no rules | rewire or remove (owner's go) |
| Demo reset (open reviewer remarks, non-blocking) | no timeout on the reset script (a hang would block wallet calls); if a reset fails the UI leaves the account on Parent; `story_replay.mjs` may leave Chrome running if it crashes; `reset_demo_wallet.py` would create wallet tables in a non-wallet sqlite file if `WALLET_DB` pointed at one | keep `ALLOW_DEMO_RESET` off outside the demo. Done: Origin check on the reset (`APP_ORIGINS`, default localhost/127.0.0.1:6274; other web pages get 403, a local program can still forge the header) |
| Auto-merge job is skipped when a push and the label arrive together | PR stays open | re-apply the label; fix: trigger on the label event without cancelling it |
| OpenAI key pasted in a chat | key may leak | revoke after the event; the key is only in the git-ignored `.env` |
| Real model differs from the fake one | a demo question may loop or lose the product reference | run the two demo questions once with the real model before the demo; the story uses the deterministic assistant |
| Git from the Claude desktop sandbox | lock files left in `.git` | run git only in your own terminal or Claude Code |

## Rules that always apply
`CLAUDE.md` and `doc/tasks/lessons.md`: plan first, diagram before code, header on every file, never delete
without approval, proof before done, `main` only through pull requests.
