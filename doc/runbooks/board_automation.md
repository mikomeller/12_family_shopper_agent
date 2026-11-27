<!--
Author:    mikomeller
Version:   0.1.0
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
| opened, reopened, ready for review, title edited (not a draft) | Ideas, Backlog, Ready | **In progress** |
| same | In progress, Test, Demo-ready, none | unchanged |
| closed and merged | none, Ideas, Backlog, Ready, In progress | **Test**, plus one comment: `Moved to Test by the board automation: pull request #<n> "<title>" was merged (<sha>).` |
| closed and merged | Test, Demo-ready | unchanged, no comment |
| closed without merge | any | nothing |

Running twice changes nothing and posts no second comment.

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
- The title is untrusted text: it goes into the script only through an environment variable, and only digits are used.

## Manual fallback
`python3 scripts/board.py move <n> "<Stage>"`. Try the automation without changes:
`python3 scripts/board_sync.py --dry-run --event merged --pr 9999 --title "feat: x (#7)" --sha abc1234`.
