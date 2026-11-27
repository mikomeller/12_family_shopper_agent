<!--
Author:    mikomeller
Version:   0.1.3
Filename:  CLAUDE.md
Pathname:  CLAUDE.md
Purpose:   Project rules and context for AI assistants working in 12_family_shopper_agent
-->
# CLAUDE.md — 12_family_shopper_agent

## Context
Hackathon entry for the Affinidi **TrustBoris** challenge (AI Agents Berlin).
A family shopping agent searches and compares products via the official **idealo MCP**
(read-only) and orders through our own **Family Wallet MCP**, which enforces individual
and family monthly spending caps. Boris adds caller identity, MCP tool gating per role,
screening, throttling, caching and backup models.

Research: `doc/research/affinidi_boris_idealo.md` · Diagrams: `doc/diagrams/` · Evals: `doc/evals/eval_plan.md`
State and next steps: `doc/handover/HANDOVER.md` · `doc/tasks/pending.md`

## Orchestration
Start with `claude --agent orchestrator`. It works from the GitHub Project board (`scripts/board.py`) and delegates to
`architect` and `reviewer` (Opus) and `wallet-dev`, `test-eval`, `docs-demo` (Sonnet) in `.claude/agents/`.
Source of the agent files is `doc/agents/`; after a change run `mkdir -p .claude/agents && cp doc/agents/*.md .claude/agents/`.
Board model: Epic = parent issue (`type:epic`), Story = sub-issue, Task = checkbox in the story.

## Rules
- Read existing files and `doc/tasks/lessons.md` before every task.
- Plan first for anything with 3+ steps: write it to `doc/tasks/todo.md` with checkboxes; ask for go before executing.
- A clear Mermaid/PlantUML diagram exists before code is written.
- Every file that allows comments starts with a header: Author, Version, Filename, Pathname, Purpose.
  Version `0.x.y`: x starts at 1 and only increases with a minor version announced by the owner; y increments with every change.
- Python is the default language. Simplicity first, minimal impact, find root causes.
- Never mark a task done without proof that it works (tests, run output).
- Never delete files without explicit approval.
- After any correction, add the lesson and the preventing rule to `doc/tasks/lessons.md`.
- Default document format is Markdown.
- Branching: `main` is reserved for reviewed code and only changes through pull requests.
  Every collaborator works on a branch named after their GitHub login (`scripts/create_collaborator_branches.py`).
