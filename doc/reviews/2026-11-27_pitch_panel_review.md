<!--
Author:    rhaveen (with Claude Code)
Version:   0.1.0
Filename:  2026-11-27_pitch_panel_review.md
Pathname:  doc/reviews/2026-11-27_pitch_panel_review.md
Purpose:   Panel review of pitch/pitch.md (origin/main, v0.1.0), the demo script and README.md for the
           Affinidi TrustBoris challenge. Five reviewers with different backgrounds. Review only, no rewrite.
-->
# Pitch panel review (2026-11-27)

## What we reviewed
- `pitch/pitch.md` v0.1.0 on `origin/main` (9 slides, Marp). `pitch.html` is built from it.
- `doc/demo/demo_script.md` v0.1.1 and `README.md` v0.1.6 on `origin/main`.
- The challenge brief `ah3-brief-affinidi-trust-boris.pdf`, page 6 (the four judging criteria).

We checked each claim against the eval results, the handover and the demo code. Branch `rodrigo-agent` does not have the `pitch/` folder. It is 19 commits behind `main`.

## Fact check: claims in the deck

| Slide | Claim | What the repo says | Verdict |
|---|---|---|---|
| 1 | "An agent that buys for your kids on its own" | Orders are simulated. Only the teen orders alone. The child must ask. | Overclaim. Say "orders" and name the teen. |
| 4, 6 | Boris sits in the live path and does identity, gating, screening, throttle, cache, backup | `boris login` not done. No Boris agent in Agent Builder. Demo script marks every Boris claim UNVERIFIED. L4 gating is a simulation. | **Not true today.** Biggest risk. |
| 5 | Step 2: teen tries 300 EUR headphones, gets a cap refusal | Browser variant of the demo script: the same headphones are blocked as INFLATED. Price in the mock is 299 EUR. | Slide and browser demo disagree. |
| 5 | Step 4: fake discount blocks the order | Works in the web UI purchase path. `scripts/demo.py` scene 4 is unverified against the block rule. | Partly verified. |
| 5 | Step 5: forged token and injected text give "zero extra orders" | Forged token: only in `scripts/demo.py`. The browser uses a demo header, not a token. Injection: S-04 adversarial driver makes **2 orders per run** (within the cap). | "Zero extra orders" is false for the adversarial run. |
| 7 | 72 / 72 pass (L1, L2) | `evals/results/2026-11-27_l1_l2.md` | True. |
| 7 | 13 scenarios, 3 / 3, all pass | S-01 to S-13 pass with the scripted driver. Adversarial rows pass where they apply. LLM rows are all SKIPPED. | True, but no LLM ran. |
| 7 | Full suite 144 passed | 144 passed, **13 skipped** | Incomplete. Add "13 skipped". |
| 7 | With vs without gating: caps held in every run | True. But orders are the same with and without gating. | True, and it weakens "what breaks without Boris". |
| 8 | "One wallet, a handful of tools" | The wallet has 8 tools. The demo script says 5. | Pick one number: 8. |
| 9 | "Agent Pay (Affinidi, coming soon)" | Research doc lists it as "coming soon" in the Trust Fabric. | OK. |
| 1 | Repo link | Repo is **public**. README still says "private". | Fix README. |

## The panel

### 1. Affinidi judge (scores the four criteria on page 6 of the brief)

| Criterion | Brief asks | Score /10 | Comment |
|---|---|---|---|
| A job worth doing | Would someone use this tomorrow? | 7 | Clear, familiar job. The demo runs on a mock catalogue, so "tomorrow" is a stretch. |
| Trust you can see | What breaks without Boris? | 4 | Boris is drawn in the path but is not connected. Our own L4 table shows the caps hold with gating off. A judge will ask to see Boris and we cannot show it. |
| More freedom, safely | What did you let it do alone? | 8 | Strong answer: the teen spends real budget without a parent. The table on slide 3 says this well. |
| Only what matters | Why is each one there? | 7 | Slide 6 gives one reason per feature. Good. But five features that are not switched on read as feature tourism. |
| **Total** | | **26 / 40** | |

Top issues:
1. Show at least one real Boris control in the demo (identity or tool gating), or say plainly that Boris is designed in but not yet connected.
2. Answer "What breaks without Boris?" with the honest split: the wallet holds the money. Boris hides tools the caller must not see, stops quota burn and screens idealo text.
3. Drop the claim that injected text gives zero orders.

### 2. Security engineer

Score: **6 / 10**

- Good: money in integer cents, cap check and order in one transaction, wallet enforces roles itself, forged token refused. This is real defence in depth.
- Problem: the browser demo uses the header `X-Family-Member`. Anyone who can reach the port can act as the parent. The deck does not say this.
- Problem: an injected "order 10" still made 2 orders in S-04. The cap limited the damage. It did not stop the purchase. Say "the cap limits the damage", not "refused".
- Problem: the discount check runs in the Node server, not the wallet. An agent that skips it is limited only by the caps. The deck implies the block is absolute.
- Ask: put the honest status in normal text size, not 0.6em. Judges who read small print will lose trust in the whole deck.

### 3. Parent (end user)

Score: **7 / 10**

- I understand slide 3 at once. Teen 50 EUR alone, child 20 EUR with my OK. That is what I want.
- Slide 2 opens with "Every family has the same two bad options". I am not sure. Ask me a question instead, like the speaker note does ("who approved a 9.99 EUR order this week?"). That works.
- Slide 4 (the ASCII diagram) means nothing to me. Show me the screen where I approve or reject.
- I want to see the refusal message my teen gets. "Refused, 39.01 EUR left" is the moment I trust it. Put it on screen big.
- Missing: what happens at the end of the month? Does the cap reset? The deck does not say.

### 4. Pitch coach (3 minute stopwatch)

Score: **5 / 10**

- Timing does not fit. The demo script gives the five scenes 180 seconds. The deck adds 8 more slides. That is 5 to 6 minutes.
- Cut to: hook (15 s), slide 3 table (20 s), live demo of 3 scenes (100 s), proof and honest status (25 s), close (20 s).
- Keep scenes 1 (teen buys), 3 (child asks, parent approves or rejects) and 4 (INFLATED block). Move scenes 2 and 5 to a backup slide.
- Nobody has clicked the browser demo through. Rehearse it twice on the demo machine. Keep `scripts/demo.py` open in a second tab as the fallback.
- Strong close line: "Hand your kids an agent, not your credit card." Keep it. Say it last, with the repo link on screen.

### 5. Copy reviewer (pitch-writer: 15 Ogilvy criteria plus "Sounds human", 6.25 each)

| # | Criterion | Score | Comment |
|---|---|---|---|
| 1 | Positioning | 5.0 | Clear what and who. "Buys for your kids" blurs teen vs child. |
| 2 | Unique benefit | 5.5 | "Spends without asking you, never above the cap" is strong. Said once, then lost. |
| 3 | Headline | 5.0 | "Pocket money with guardrails" is good. |
| 4 | Reader focused | 4.0 | Slides 4, 6, 7 talk about us and our stack, not the judge's question. |
| 5 | Clear tone | 4.0 | Plain, but claims run ahead of the facts (Boris, zero orders). |
| 6 | Simple language | 3.5 | "L1, L2, L4", "tool contract", "adversarial driver" need a word of context. |
| 7 | Evidence | 4.5 | Real numbers. Lose points for "144 passed" without "13 skipped" and for the S-04 claim. |
| 8 | Emotion / story | 3.5 | No family, no moment. Give the teen a name and one real purchase. |
| 9 | Structure | 5.0 | Mapped to the four criteria. Good. Too many slides. |
| 10 | Call to action | 3.5 | No clear ask. Say what you want: try the repo, the one command to run it. |
| 11 | Visuals | 3.0 | ASCII diagram and dense tables. No screenshot of the app. |
| 12 | Testability | 4.5 | The eval suite is the test. Good. |
| 13 | Length | 3.0 | Too long for 3 minutes. |
| 14 | Attention grabbing | 4.0 | The hook question is in the speaker note, not on the slide. |
| 15 | Repetition | 4.0 | The close line comes once. Use it on slide 1 and the last slide. |
| 16 | Sounds human | 2.5 | 15+ em dashes, bold in almost every line, "Proof, not promises", "Defence in depth", "no feature tourism". These read as AI copy and break the house style. |
| | **Total** | **64.5 / 100** | |

Top 3 weaknesses: honesty about Boris (5, 7), length and slide count (9, 13), AI-sounding style (16).

## Panel summary

| Reviewer | Score |
|---|---|
| Affinidi judge | 26 / 40 (65 %) |
| Security engineer | 6 / 10 |
| Parent | 7 / 10 |
| Pitch coach | 5 / 10 |
| Copy reviewer | 64.5 / 100 |

All five agree: the idea and the wallet are strong. The deck claims more Boris than the repo has, and it is too long for 3 minutes.

## Ranked fix list

1. **Boris status.** Before the pitch, try to connect one real control (identity or tool gating) and show it live. If that fails, change slides 4 and 6 to "Designed for Boris. Not yet connected." and put that in normal text.
2. **"What breaks without Boris?"** Answer with our own L4 data: the wallet holds the money either way. Boris hides tools the child must not see, protects the idealo quota (500 calls a day) and screens untrusted product text.
3. **Fix false or loose claims.** S-04: "the cap limited the damage", not "zero extra orders". Add "13 skipped". One tool count (8). "Orders" not "buys". Say the demo uses an idealo mock if no key is set.
4. **Align slide 5 with the browser demo.** Use the same scene order and the same outcome for the headphones.
5. **Cut to 5 or 6 slides** and 3 live scenes. Move the rest to backup slides.
6. **Add one app screenshot** (the refusal with the amount left, or the parent approval screen). Drop the ASCII diagram or move it to backup.
7. **Style pass.** Remove every em dash and most bold. Remove "Proof, not promises", "Defence in depth", "feature tourism". Short plain sentences.
8. **Rehearse the browser demo** twice. Nobody has clicked it through yet.
9. **README.** Add a 5 line "For judges" block at the top: what it is, one command to run it, what is real and what is mocked. Fix "private" to "public". Move the GitHub board setup and the personal Mac path to a separate doc.

## What a human must still decide
- Can someone connect Boris before the pitch? This decides fix 1.
- Who presents, and on which machine?
- Do you run the demo with an OpenAI key (real idealo) or offline (mock)?

## After the rewrite (same day, branch `rhaveen-sa`)
Changed: `pitch/pitch.md` v0.1.1 (6 main slides plus 3 backup), `pitch/pitch.html` (rebuilt), `doc/demo/demo_script.md` v0.1.2, `README.md` v0.1.7.

Copy reviewer, second score:

| # | Criterion | Before | After | Why |
|---|---|---|---|---|
| 1 | Positioning | 5.0 | 5.5 | "Your teen's agent orders on its own" names who and what. |
| 2 | Unique benefit | 5.5 | 5.5 | Same benefit, now on slide 1 and in the README. |
| 3 | Headline | 5.0 | 5.0 | Unchanged. |
| 4 | Reader focused | 4.0 | 5.0 | Slides answer the judges' four questions. Stack moved to backup. |
| 5 | Clear tone | 4.0 | 5.5 | Claims match the repo. Boris status said in normal text. |
| 6 | Simple language | 3.5 | 5.0 | "L1, L2, L4" and "adversarial driver" replaced with plain words. |
| 7 | Evidence | 4.5 | 5.5 | 152 passed, 13 skipped. The 2 backpack finding is stated. |
| 8 | Emotion / story | 3.5 | 4.0 | Opening question to the room. Still no named family. |
| 9 | Structure | 5.0 | 5.5 | 6 slides in the order of the talk. |
| 10 | Call to action | 3.5 | 5.0 | One command to try it, on the last slide and in the README. |
| 11 | Visuals | 3.0 | 3.0 | Still no app screenshot. |
| 12 | Testability | 4.5 | 4.5 | Unchanged. |
| 13 | Length | 3.0 | 5.0 | Fits 3 minutes on paper. Not timed yet. |
| 14 | Attention grabbing | 4.0 | 4.5 | The hook question is in the notes and the script. |
| 15 | Repetition | 4.0 | 4.0 | The close line appears once. |
| 16 | Sounds human | 2.5 | 5.0 | No em dashes, no comma before "and", bold only on role names and two labels. |
| | **Total** | **64.5** | **77.5** | |

Still open:
- Add one screenshot of the app (the refusal with the amount left, or the parent approval) to slide 3.
- Rehearse the browser demo and time it. Steps 2 and 5 are planned from the server code, not seen on screen.
- If Boris gets connected before the pitch, update slide 4, slide 5 and the README status line.

## Third round: Rings deck (pitch/pitch.html v0.3.0) and product README (v0.1.8)
Proof run after the last edit: `uv run pytest -q` 152 passed, 13 skipped. `evals -m "l3 or l4"` 28 passed, 13 skipped.
`evals/run_report.py` reproduced the same results files. `scripts/demo.py` DEMO OK: 5/5 scenes. `ruff` clean.
No em or en dashes and no comma before "and" in the deck, the README or the demo script.

Copy reviewer (pitch-writer, 16 criteria, 6.25 each):

| # | Criterion | Round 1 | Round 2 | Round 3 | Why it moved |
|---|---|---|---|---|---|
| 1 | Positioning | 5.0 | 5.5 | 6.0 | Cover now says live idealo, own model, limits in the wallet. |
| 2 | Unique benefit | 5.5 | 5.5 | 5.5 | |
| 3 | Headline | 5.0 | 5.0 | 5.0 | |
| 4 | Reader focused | 4.0 | 5.0 | 5.0 | |
| 5 | Clear tone | 4.0 | 5.5 | 5.5 | |
| 6 | Simple language | 3.5 | 5.0 | 5.0 | |
| 7 | Evidence | 4.5 | 5.5 | 5.5 | Rings show the real numbers from the demo run. |
| 8 | Emotion / story | 3.5 | 4.0 | 4.5 | "One family, five orders" with a ring per person. |
| 9 | Structure | 5.0 | 5.5 | 5.5 | |
| 10 | Call to action | 3.5 | 5.0 | 5.5 | Closing slide gives the real setup: connect idealo, add a key. |
| 11 | Visuals | 3.0 | 3.0 | 5.5 | One visual idea (spending rings) on every key slide. Still no app screenshot. |
| 12 | Testability | 4.5 | 4.5 | 4.5 | |
| 13 | Length | 3.0 | 5.0 | 5.0 | 8 main slides, two of them 5 to 15 seconds. Not timed yet. |
| 14 | Attention grabbing | 4.0 | 4.5 | 5.0 | Animated rings on the cover. |
| 15 | Repetition | 4.0 | 4.0 | 5.0 | Rings and the gradient word repeat from cover to closing line. |
| 16 | Sounds human | 2.5 | 5.0 | 5.0 | |
| | **Total** | **64.5** | **77.5** | **83.0** | |

Affinidi judge, second look: criterion 2 (Trust you can see) stays the weakest at 5 of 10 until Boris runs on the live agent.
The other three criteria rise to 8 each with the live idealo MCP and own model on the cover. Total about 29 of 40.

Still open: an app screenshot on slide 3, a timed rehearsal, Boris on the live agent.

## 2 minute script (pitch/pitch_script_2min.md v0.1.0)
pitch-writer score: 78.0 of 93.75 points (Visuals is n/a for a spoken script), scaled to **83 / 100**.
Strongest: positioning (6.0), simple language, length (about 255 words, 1:50 at 140 words a minute).
Weakest: testability (4.5), repetition (4.5: the close line comes once), call to action (5.0: "the code is on GitHub" names no link).
Before it goes out: say the repo name out loud at the close, and time it once with a stopwatch.
