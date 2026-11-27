<!--
Author:    mikomeller
Version:   0.1.4
Filename:  README.md
Pathname:  README.md
Purpose:   Overview, structure and first-time setup of 12_family_shopper_agent
-->
# 12_family_shopper_agent

A family shopping agent built on Affinidi **TrustBoris** for the AI Agents Berlin hackathon (Affinidi challenge).
It searches and compares products through the official **idealo MCP** and **orders on its own**,
within each member's and the family's monthly spending caps.

**Trust dividend:** spending money without a parent approving every order.

| Role | May do | Monthly cap |
|---|---|---|
| Parent | everything, approves requests, sets budgets | none (family cap applies) |
| Teen | search and order alone | €50 |
| Child | search; every order becomes an approval request | €20 |
| Family | all orders together | €400 |

Architecture: [`doc/diagrams/family_buyer_architecture.mmd`](doc/diagrams/family_buyer_architecture.mmd) ·
Purchase flow: [`doc/diagrams/purchase_decision_sequence.mmd`](doc/diagrams/purchase_decision_sequence.mmd) ·
Research: [`doc/research/affinidi_boris_idealo.md`](doc/research/affinidi_boris_idealo.md)

## Structure
```
.github/ISSUE_TEMPLATE/   Idea, Task, Bug issue forms
config/                   family_budget.example.yaml (copy to family_budget.yaml)
doc/research/             research and spike results
doc/diagrams/             Mermaid diagrams (before code)
doc/agents/               orchestrator + subagents for Claude Code; copy to .claude/agents/, then: claude --agent orchestrator
doc/evals/                eval_plan.md (gates, eval levels, scenarios)
doc/handover/             HANDOVER.md (state, decisions, how to start)
doc/tasks/                todo.md (plan), pending.md (next steps) and lessons.md
scripts/                  setup_github.py + backlog.json, board.py (board in the terminal)
```

## First-time GitHub setup (on your Mac, from `~/Documents/M1_20230921/src/genAI/12_family_shopper_agent`)
```bash
brew install gh                      # if missing
gh auth login                        # if not logged in as mikomeller
gh auth refresh -s project           # Projects scope
python3 scripts/setup_github.py --dry-run   # check, no network
python3 scripts/setup_github.py             # creates repo, labels, milestones, Project, fields, 40 issues (7 epics), epic links
```
The script creates the **private** repo `mikomeller/12_family_shopper_agent`, makes the first commit and pushes.
It is safe to re-run. If your Project already has another number, pass `--project-number <N>`.

Then, once, in the Project: **New view → Board → Column by: Stage**, and under **Workflows** enable
**Auto-add to project** for this repo so new issues land on the board.

## Branches
`main` is reserved for reviewed code and only changes through pull requests.
Every collaborator gets a branch named after their GitHub login, started from `main`:
```bash
python3 scripts/create_collaborator_branches.py --dry-run   # shows who gets which branch
python3 scripts/create_collaborator_branches.py
```
Covers accepted collaborators and pending invitations (owner skipped). Re-run after inviting new people.

## Before the hackathon kickoff
Docker running · `brew install --cask affinidi-ai/tap/boris` · `boris doctor` ·
`boris login --url https://trustboris.ai` · use Chrome (not Safari). See milestone **M0 Pre-kickoff**.
