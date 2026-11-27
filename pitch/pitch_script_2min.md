<!--
Author:    rhaveen-sa (with Claude Code)
Version:   0.1.0
Filename:  pitch_script_2min.md
Pathname:  pitch/pitch_script_2min.md
Purpose:   Spoken 2 minute product pitch for Family Shopper Agent (about 255 words at 140 words a minute).
           Goes with pitch/pitch.html. Facts checked against README.md and evals/results/ on 2026-11-27.
-->
# Family Shopper Agent: 2 minute pitch

## Script

**0:00 Hook** (slide 1)
Hands up if you approved a ten euro book order on your phone this week.
That is the job we gave to an agent.

**0:10 The problem** (slide 2)
Parents have two choices today. Hand the kids the card and hope. Or approve every single order.
Shopping agents make this harder, because they can search and buy in seconds.

**0:25 What we built** (slide 2)
Family Shopper Agent holds the family's pocket money for them.
A teen gets 50 euro a month and the agent orders for them alone. No parent asked.
A child gets 20 euro. Every order waits for a parent's yes.
The whole family stays under 400 euro.

**0:45 How it works** (slide 3 or live app)
It searches real offers through the official idealo MCP.
You bring your own model: OpenAI, Nebius or any compatible endpoint. The key stays in memory.
Watch the teen buy a book for 10.99. Done, 39.01 left.
Now a 59.99 controller. It does not fit. The agent says so and tells the teen what is left.

**1:10 Why you can trust it** (slide 5)
The limits are not in the prompt. They live in our Family Wallet.
It checks the limit and writes the order in one step. It refuses a child's direct order, whatever the model asks.
TrustBoris is the layer around the agent. We designed it in to decide who is calling, which tools they see and what text reaches the model.

**1:35 Proof** (slide 6)
152 tests pass. We ran 13 family scenarios with a driver that breaks every rule. It never got past a limit.

**1:50 Close** (slide 7)
Hand your kids an agent, not your credit card.
It runs with one Docker command. The code is on GitHub. Thank you.

## Notes for the speaker
- Speak at about 140 words a minute. The script is about 255 words, so you have about 10 seconds spare for the live step.
- If you show the live app at 0:45, have the teen signed in and the book already searched.
- If someone asks whether Boris is running: it is designed in and the CLI runs, but the agent is not yet connected in Agent Builder. Say it plainly.
- If someone asks about live orders: search is live on idealo. Orders are recorded in the wallet with the shop link. The app does not pay the shop.
