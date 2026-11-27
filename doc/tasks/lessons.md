<!--
Author:    mikomeller
Version:   0.1.5
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
- **2026-11-27 — Script could not recover from a half-finished step.** `gh repo create --source --remote --push` created the
  repo and set `origin`, then failed with "Unable to add remote origin" and skipped the push; a re-run would have skipped the push too.
  *Rule:* each setup step checks the real end state (repo exists? origin set? upstream set?) instead of trusting one combined command;
  test the re-run path, not only the happy path.
- **2026-11-27 — Nobody was invited.** Neither setup script sends repo invitations; the branch script only reads people who are
  already invited, and I never asked for the collaborators' GitHub usernames.
  *Rule:* when a step depends on people, ask for their usernames explicitly and say plainly which script invites them (and which doesn't).
- **2026-11-27 — idealo MCP is read-only** (no checkout; idealo Checkout ended 2022).
  *Rule:* every "buy" goes through our Family Wallet MCP; never assume a shop API can order.
- **2026-11-27 — Re-running the setup script would have reset the board.** `setup_github.py` wrote Stage, Priority and the
  other fields on every run, also for existing issues, so a re-run would have moved cards the team had already moved.
  *Rule:* a re-runnable script sets values only on what it creates in that run; test the re-run against a changed state.
- **2026-11-27 — YAML front matter broke on a colon.** A subagent `description` containing ": " is not valid unquoted YAML.
  *Rule:* quote every front-matter string and parse each agent file once before delivering it.
- **2026-11-27 — `.claude/` cannot be written from the Claude desktop app.** The agent files were rejected there.
  *Rule:* keep agent definitions in `doc/agents/` as the source and install them with a copy command run by the owner.
