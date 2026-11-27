<!--
Author:    rhaveen-sa (with Claude Code)
Version:   0.1.1
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
A teen gets 50 euro a month, a child 20. The agent orders for them alone, up to that budget.
Above it, the wallet refuses and a parent steps in: the member asks, the parent approves or rejects.
A parent-approved order counts against the member's budget and the family's 400 euro.
Up to the budget the trust layer decides. Above it, a parent steps in.

**0:45 How it works** (slide 3 or live app)
It searches real offers through the official idealo MCP.
You bring your own model: OpenAI, Nebius or any compatible endpoint. The key stays in memory.
Press Play the story. The child asks for Der Hobbit. idealo compares, the best offer is 10,99. The child orders. Done, 9,01 left.
Now a board game for 30,98. Above the budget, so it is refused with the reason. The child asks a parent, the parent approves, and the family budget pays. 358,03 left.

**1:10 Why you can trust it** (slide 5)
The limits are not in the prompt. They live in our Family Wallet.
It checks the limit and writes the order in one step. It refuses an order above a member's budget, whatever the model asks.
TrustBoris is the layer around the agent. We designed it in to decide who is calling, which tools they see and what text reaches the model. It is not connected in the demo. The gateway steps in the story are simulated and labelled so.

**1:35 Proof** (slide 6)
191 tests pass. We ran 16 family scenarios, three runs each, with a driver that breaks every rule. It never got past a limit, and never ordered above a member's budget without a parent's approval. These ran at the tool layer, not with a language model.

**1:50 Close** (slide 7)
Hand your kids an agent, not your credit card.
It runs with one Docker command. The code is on GitHub. Thank you.

## Notes for the speaker
- Speak at about 140 words a minute. The script is about 255 words, so you have about 10 seconds spare for the live step.
- If you show the live app at 0:45, open http://localhost:6274/?story=1 and press Play the story.
- If someone asks whether Boris is running: it is designed in and the CLI runs, but it is not connected in the demo and the agent is not yet in Agent Builder. The gateway steps in the story are simulated. The wallet enforces the limits. Say it plainly.
- If someone asks about live orders: search is live on idealo. Orders are recorded in the wallet with the shop link. The app does not pay the shop.
