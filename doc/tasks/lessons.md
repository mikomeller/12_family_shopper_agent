<!--
Author:    mikomeller
Version:   0.1.8
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
- **2026-11-27 — Worktree tool cannot enter a main checkout**, and the owner requires work in the one allowed folder.
  *Rule:* work in place in `~/Documents/M1_20230921/src/genAI/12_family_shopper_agent`; do not use the worktree tool there.
- **2026-11-27 — `uv run python -m family_shopper...` failed with ModuleNotFoundError** because the editable-install `.pth` file in `.venv` gets the macOS hidden flag (pytest is unaffected).
  *Rule:* start servers with `PYTHONPATH=src uv run python -m ...`.
- **2026-11-27 — pytest exits with code 5 when no tests exist**, so a CI bootstrap without tests fails.
  *Rule:* a CI bootstrap needs at least one smoke test.
- **2026-11-27 — `astral-sh/setup-uv` has no floating major tag.**
  *Rule:* pin the exact release tag of every GitHub Action; check that the tag exists before using it.
- **2026-11-27 — A second clone was made in `~/github/`** before the owner named the allowed folder.
  *Rule:* ask for the working folder before cloning anything (the old rule "confirm the working directory" applies to clones too).
- **2026-11-27 — Ticket #25's formula was not sound.** `claimed_discount >= (list_price - 30_day_low) / list_price` reduces to `sale <= 30_day_low` and never tests the "was" price.
  *Rule:* check a collaborator ticket's formula with numbers before building it.
- **2026-11-27 — A premise stayed unverified.** The owner believed Boris and OpenAI credentials were in a collaborator's branch; I did not say it was unverified until I checked. They were not there, and they must not be (public repo).
  *Rule:* check a claimed location of secrets before planning on it; never ask for secrets to be committed.
- **2026-11-27 — PR #56 was merged before the independent review** because of the deadline.
  *Rule:* say so in the PR and the handover and run the review right after; with auto-merge on, the review happens before the `automerge` label is set.
- **2026-11-27 — A smoke test asserted on wording changed after its last run.**
  *Rule:* re-run the proof after the last edit, not before it.
- **2026-11-27 — Docker: `uv run` inside the image tried to re-sync a read-only venv.**
  *Rule:* set `UV_NO_SYNC=1` and use `PYTHONPATH` in the app image.
- **2026-11-27: The first pitch deck claimed more than the repo had.** It showed Boris in the live path, said injected text gave "zero extra orders" (S-04 made 2) and gave an old test count.
  *Rule:* before a pitch or README goes out, check every claim against `evals/results/` and the handover, and say what is simulated in normal text size.
