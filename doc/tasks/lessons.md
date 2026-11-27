<!--
Author:    mikomeller
Version:   0.1.1
Filename:  lessons.md
Pathname:  doc/tasks/lessons.md
Purpose:   Lessons learned and the rules that prevent repeating mistakes; review at the start of every session
-->
# Lessons

- **2026-11-27 — GitHub owner.** I first proposed the Tfitconsult/indietonne2 accounts; the project belongs to **mikomeller**, which is not connected to Claude's GitHub session.
  *Rule:* confirm the GitHub owner before proposing or attaching a repo; for mikomeller, deliver a local `gh` script.
- **2026-11-27 — GitHub Projects need GraphQL**, which Claude cloud sessions cannot use.
  *Rule:* create and populate Projects through a local `gh` script (`scripts/setup_github.py`).
- **2026-11-27 — Wrong working folder.** The scaffold was written to the Google Drive folder, but the git working copy is
  `~/Documents/M1_20230921/src/genAI/12_family_shopper_agent`; running the script there failed with "No such file".
  *Rule:* confirm the working directory (where git and scripts run) before writing files, and state the full path to run from.
- **2026-11-27 — idealo MCP is read-only** (no checkout; idealo Checkout ended 2022).
  *Rule:* every "buy" goes through our Family Wallet MCP; never assume a shop API can order.
