<!--
Author:    mikomeller
Version:   0.1.1
Filename:  board_automation.md
Pathname:  doc/runbooks/board_automation.md
Purpose:   Runbook: the GitHub Project board follows pull request titles automatically; one-time setup, limits, fallback
-->
# Board automation

The workflow `.github/workflows/board-sync.yml` ("Board sync") runs `scripts/board_sync.py` and moves the cards of the
GitHub Project `12_family_shopper_agent` when pull requests open and merge.

## Title convention
Name the stories in the pull request **title**: `feat: wallet server (#7, #8)` or `fix: cap check (#58)`.
Only issue numbers in the title count. A `#NN` in the body is just a mention. Numbers that are pull requests are ignored
(GitHub appends the PR's own ` (#NN)` to squash commit titles), and issues labelled `type:epic` are never moved.

## What it does
| Pull request event | Stage of the named issue | Result |
|---|---|---|
| opened, reopened, ready for review, title edited (not a draft; same-repository pull request by owner, member or collaborator) | Ideas, Backlog, Ready | **In progress** |
| same | In progress, Test, Demo-ready, none | unchanged |
| closed and merged | none, Ideas, Backlog, Ready, In progress | **Test**, plus one comment: `Moved to Test by the board automation: pull request #<n> was merged (<sha>).` and a hidden marker `<!-- board-sync pr=<n> -->` |
| closed and merged | Test | unchanged; comment added once if this pull request has no marker comment yet |
| closed and merged | Demo-ready | unchanged, no comment |
| closed without merge | any | nothing |

Running twice changes nothing and posts no second comment. A comment counts as existing only if it was written by
`github-actions[bot]` and holds the exact marker of this pull request (so #9 and #99 do not collide and a user cannot
suppress the comment by typing the marker). Behaviour note: a merged pull request that names a story already in Test
adds its comment once; nothing else changes. If only the comment fails, the card is still moved, the run exits 1, and a
re-run posts the missing comment. Only items of this repository are matched. If the project holds 500 or more items the
run prints `warning: project has <n>+ items; raise the limit`.

## What it never does
- It never sets **Demo-ready** (a person has to see it work).
- It never ticks checkboxes, closes issues or moves epics.
- It never reads the pull request's code: the workflow and the script always come from `main`.

## One-time setup (owner)
1. Create a classic personal access token at github.com → Settings → Developer settings → Personal access tokens (classic)
   with ONLY the scope `project`, an expiry, and the name "family-shopper board sync".
2. In a terminal run `gh secret set PROJECT_TOKEN --repo mikomeller/12_family_shopper_agent` and paste the token.
3. Check: open any pull request with `(#<issue>)` in the title and look at the "Board sync" run in the Actions tab.

Without the secret the workflow still runs and prints `board sync skipped: no PROJECT_TOKEN secret configured`.

## Security notes
- The token can edit the owner's project boards and nothing else (no repository access).
- Collaborators with write access can change workflows on `main` (there is no branch protection) and could misuse any
  repository secret. That is why the token has only the `project` scope.
- The issue comment uses the built-in `GITHUB_TOKEN` (permission `issues: write` for this job only).
- Who can trigger card moves: for In progress only same-repository pull requests (no forks) by the owner, members or
  collaborators, so the secret is not handed to runs triggered by outsiders; for Test any merged pull request (a
  maintainer merged it).
- The title is untrusted text: it goes into the script only through an environment variable, passed as `--title="$PR_TITLE"`
  so a title starting with `--` is not read as an option, and only digits are used.
- The comment never contains pull request text (no title, no `@mentions`, no markdown): only the number and the short sha.
- The job has `contents: read` and `issues: write` only; checkout does not persist credentials.

## Manual fallback
`python3 scripts/board.py move <n> "<Stage>"`. Try the automation without changes:
`python3 scripts/board_sync.py --dry-run --event merged --pr 9999 --title "feat: x (#7)" --sha abc1234`.
