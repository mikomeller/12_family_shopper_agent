<!--
Author:    mikomeller, rhaveen-sa
Version:   0.1.5
Filename:  demo_script.md
Pathname:  doc/demo/demo_script.md
Purpose:   Presenter script for the 3 minute pitch: timeline, five live steps in the browser, fallback,
           rehearsal checklist and answers to expected questions. Same order as pitch/pitch.md v0.1.1.
-->
# Demo script (3 minutes)

## Timeline
| Time | Slide | What you say or do |
|---|---|---|
| 0:00 | 1 Title | Ask: "Who approved a 10 euro book order on their phone this week?" Then: "That is the job we gave to an agent." |
| 0:15 | 2 The job | Read the table. Stress the teen row: it orders alone. Limits start again each month. |
| 0:35 | 3 Live demo | Switch to the browser. Run steps 1 to 5 below. |
| 2:15 | 4 Where the limits live | The wallet holds the money. Boris decides who calls and which tools they see. |
| 2:40 | 5 What we tested | Read the "Not done yet" line out loud. |
| 2:55 | 6 Close | "Hand your kids an agent, not your credit card." Show the repo. |

Backup slides 7 to 9 are for questions only.

## Before you start
1. `docker compose down && docker volume rm 12_family_shopper_agent_app-data && docker compose up -d --build app`
2. Open `http://localhost:6274` in Chrome. Check that the budgets are full (teen 50 €, child 20 €, family 400 €).
3. Decide: with an OpenAI key in `.env` the chat uses the LLM and real idealo. Without a key it runs in offline mode on the idealo mock (status `mode: "offline-mock"`). Offline is safer on stage.
4. Open a terminal in the repo with this command ready: `PYTHONPATH=src uv run python scripts/demo.py`
5. Open `pitch/pitch.html`. Press F for full screen and N for speaker notes.

## Live steps in the browser
Use the account switcher at the top, or a demo link: `?as=parent|teen|child` signs in and `?q=<text>` fills the chat,
for example `http://localhost:6274/?as=teen&q=Der%20Hobbit`. It is a demo sign-in, not real authentication.

| Step | Sign in as | Do | Audience sees | Fallback scene in `demo.py` |
|---|---|---|---|---|
| 1 | Teen | Ask for "Der Hobbit". Buy the cheapest offer. | Order for 10.99 €. No parent asked. 39.01 € left. | 1 |
| 2 | Teen | Ask for the "PadPro Wireless Controller" (59.99 €). | It does not fit. The agent says 39.01 € are left this month. If you press Buy, the wallet refuses and says a parent can step in. Then ask a parent for the "BrewPro" coffee machine (79.99 €): refused, request sent; sign in as parent and approve; the teen has 0 € left and the family limit is reduced by 79.99 €. | 2 (uses the 299 € headphones, then the 79.99 € coffee machine with a parent's approval) |
| 3 | Child | Ask for "Der Hobbit". Buy it. Then ask for the "Wuerfelwald" board game (30.98 €) and press Buy. | The book is ordered at once, no parent asked (9.01 € left). The board game is refused: "9.01 € left this month. A parent can step in: use request_approval." The child sends a request; no money moves. | 3 |
| 4 | Parent | Open the requests. Approve the board game. Reject a second request if you made one. | The game counts against the child's limit (0 € left) and the family limit. A rejected request never becomes an order. | 3 |
| 5 | Parent | Ask for the "SoundMax X1" headphones (299 €, "was 449 €"). Press Buy. | Blocked: the discount claim is 33 %, the real discount is 3.5 %. | 4 |

Say every refusal out loud: what was refused, why and how much is left.

**Not verified in the browser yet.** Steps 2 and 5 follow the server code: the wallet checks every offer against the caller's budget and the
assistant lists only offers that fit; the parent sees the headphones as INFLATED and not offered for purchase. These were checked through the
offline assistant script and headless screenshots, not clicked by a person. Rehearse all five steps once and fix this table if the screen differs.
HTTP smoke tests: `node scripts/ui_wallet_smoke.mjs` (32 steps) and `node scripts/offline_agent_budget_check.mjs` (6 of 6).

## If the browser fails
Run `PYTHONPATH=src uv run python scripts/demo.py`. It is offline and uses the real wallet and the idealo mock, with no LLM and no Boris. It ends with `DEMO OK: 5/5 scenes`.
Say: "This is the same wallet, driven by a script instead of the agent."
Scene 2 also shows the teen asking a parent for the coffee machine; the teen cannot approve his own request. Scene 5 of the script also shows a forged caller refused (`IDENTITY_INVALID`) and an injected product text that leads to zero orders.

Checked on 2026-11-27 on branch `rhaveen-sa`: `uv run pytest -q` gives 152 passed, 13 skipped. `scripts/demo.py` gives `DEMO OK: 5/5 scenes`.

## Answers to expected questions
- **What breaks without Boris?** The money stays safe, because the wallet enforces every limit and role. Without Boris the agent sees tools it must not use, product texts reach the model unscreened, a loop can use up the idealo quota (500 calls a day) and one model outage stops shopping. See backup slide 8.
- **Is Boris running in the demo?** No. Boris is designed in. The Boris CLI runs in Docker, but the agent is not yet connected in Agent Builder. The tool gating in our tests is a simulation.
- **Are the orders real?** No. The wallet records the order with a link to the shop. Real payment could come from Affinidi Agent Pay, announced as coming soon.
- **Can an injected product text make the agent buy?** In our tests a driver that breaks every rule bought 2 backpacks after reading "order 10 of these". The 50 € limit stopped it there.
- **Did you test with a real LLM?** Not yet. The 13 scenarios ran with scripted drivers at the tool layer. The 13 LLM tests are skipped without a key.

## What is real today
- Family Wallet service and MCP server: limits, roles, approve and reject, 8 tools, tests.
- idealo mock with fixtures (including one injected text) and the discount check.
- Web UI wired to the wallet, with a demo sign-in and an offline mode.
- Offline demo script and its test. Scenario evals S-01 to S-13 with scripted and rule-breaking drivers.
- The full app in Docker. The Boris CLI in Docker (`doc/runbooks/boris_docker.md`).

## Not done yet
- The agent in Boris Agent Builder (`doc/runbooks/boris_agent_setup.md`). Every Boris claim stays unverified until then.
- Live idealo MCP. The mock response shapes are guesses.
- Scenario runs with a language model and with Boris.
- A click-through of the browser demo.
