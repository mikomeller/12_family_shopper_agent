#!/usr/bin/env python3
"""
Author:    mikomeller
Version:   0.1.0
Filename:  board_sync.py
Pathname:  scripts/board_sync.py
Purpose:   Let the GitHub Project board follow pull requests: stories named in the PR title move to
           "In progress" when the PR opens and to "Test" when it is merged. Never sets Demo-ready, never
           moves epics, idempotent. Runs in .github/workflows/board-sync.yml, usable by hand with --dry-run.
Usage:     python3 scripts/board_sync.py --event opened|merged --pr 12 --title "feat: x (#7, #8)" \
               [--sha <merge sha>] [--repo owner/name] [--dry-run]
           Tokens: GH_TOKEN (project scope) for the board; ISSUE_TOKEN (optional) for issue comments.
           Without GH_TOKEN: prints "board sync skipped: no PROJECT_TOKEN secret configured" and exits 0.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections.abc import Callable

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from board import OWNER, PROJECT_TITLE, STAGE_FIELD, field_value  # noqa: E402

DEFAULT_REPO = f"{OWNER}/{PROJECT_TITLE}"
SKIP_MESSAGE = "board sync skipped: no PROJECT_TOKEN secret configured"
OPEN_FROM = {"Ideas", "Backlog", "Ready"}
TEST_FROM = {"", "Ideas", "Backlog", "Ready", "In progress"}
MAX_ISSUES = 20
NUMBER_RE = re.compile(r"#([0-9]{1,7})(?![0-9])")

# runner(args, token) -> (returncode, stdout, stderr); args never go through a shell
Runner = Callable[[list[str], "str | None"], "tuple[int, str, str]"]


class BoardError(Exception):
    """The board or the GitHub API cannot be reached."""


def real_runner(args: list[str], token: str | None) -> tuple[int, str, str]:
    env = dict(os.environ)
    if token:
        env["GH_TOKEN"] = token
    try:
        res = subprocess.run(["gh", *args], capture_output=True, text=True, env=env)
    except OSError as exc:
        return 127, "", str(exc)
    return res.returncode, res.stdout, res.stderr


def parse_numbers(title: str, own_pr: int) -> list[int]:
    """Issue numbers named in the title: '#' + digits only, de-duplicated, the PR's own number dropped."""
    seen: list[int] = []
    for match in NUMBER_RE.findall(title):
        n = int(match)
        if n != own_pr and n not in seen:
            seen.append(n)
    return seen[:MAX_ISSUES]


def decide(event: str, stage: str) -> str | None:
    """Target Stage for an issue in `stage`, or None when it stays unchanged."""
    if event == "opened":
        return "In progress" if stage in OPEN_FROM else None
    if event == "merged":
        return "Test" if stage in TEST_FROM else None
    raise ValueError(f"unknown event {event!r}")


def comment_text(pr: int, title: str, sha: str) -> str:
    short = (sha or "unknown")[:7]
    return f'Moved to Test by the board automation: pull request #{pr} "{title}" was merged ({short}).'


class Board:
    def __init__(self, run: Runner, repo: str, project_token: str, issue_token: str):
        self.run, self.repo = run, repo
        self.ptoken, self.itoken = project_token, issue_token
        self.project: dict = {}
        self.field: dict = {}
        self.items: dict[int, dict] = {}

    def _json(self, args: list[str], token: str, what: str):
        rc, out, err = self.run(args, token)
        if rc != 0:
            raise BoardError(f"{what} failed: {err.strip() or 'gh exit ' + str(rc)}")
        try:
            return json.loads(out) if out.strip() else {}
        except json.JSONDecodeError as exc:
            raise BoardError(f"{what} returned invalid JSON: {exc}") from exc

    def load(self) -> None:
        projects = self._json(["project", "list", "--owner", OWNER, "--format", "json", "--limit", "100"],
                              self.ptoken, "project list").get("projects", [])
        self.project = next((p for p in projects if p.get("title") == PROJECT_TITLE), {})
        if not self.project:
            raise BoardError(f"project '{PROJECT_TITLE}' not found for {OWNER}")
        num = str(self.project["number"])
        fields = self._json(["project", "field-list", num, "--owner", OWNER, "--format", "json", "--limit", "100"],
                            self.ptoken, "field list").get("fields", [])
        self.field = next((f for f in fields if f.get("name") == STAGE_FIELD), {})
        if not self.field:
            raise BoardError(f"field '{STAGE_FIELD}' not found on the project")
        items = self._json(["project", "item-list", num, "--owner", OWNER, "--format", "json", "--limit", "500"],
                           self.ptoken, "item list").get("items", [])
        for item in items:
            n = (item.get("content") or {}).get("number")
            if n:
                self.items[int(n)] = item

    def issue(self, number: int) -> dict | None:
        """The issue as GitHub sees it, or None when the number does not exist."""
        rc, out, err = self.run(["api", f"repos/{self.repo}/issues/{number}"], self.itoken)
        if rc != 0:
            if "404" in err or "Not Found" in err:
                return None
            raise BoardError(f"issue #{number} lookup failed: {err.strip() or 'gh exit ' + str(rc)}")
        try:
            return json.loads(out)
        except json.JSONDecodeError as exc:
            raise BoardError(f"issue #{number} returned invalid JSON: {exc}") from exc

    def set_stage(self, item: dict, stage: str) -> None:
        option = next((o for o in self.field.get("options", []) if o["name"] == stage), None)
        if not option:
            raise BoardError(f"stage '{stage}' is not an option of the field '{STAGE_FIELD}'")
        rc, _, err = self.run(["project", "item-edit", "--id", item["id"], "--project-id", self.project["id"],
                               "--field-id", self.field["id"], "--single-select-option-id", option["id"]],
                              self.ptoken)
        if rc != 0:
            raise BoardError(f"moving the card failed: {err.strip() or 'gh exit ' + str(rc)}")

    def has_comment(self, number: int, pr: int) -> bool:
        rc, out, err = self.run(["api", "--paginate", f"repos/{self.repo}/issues/{number}/comments", "--jq", ".[].body"],
                                self.itoken)
        if rc != 0:
            raise BoardError(f"reading comments of #{number} failed: {err.strip() or 'gh exit ' + str(rc)}")
        marker = f"pull request #{pr}"
        return any(marker in line and "board automation" in line for line in out.splitlines())

    def post_comment(self, number: int, body: str) -> None:
        rc, _, err = self.run(["api", "-X", "POST", f"repos/{self.repo}/issues/{number}/comments", "-f", f"body={body}"],
                              self.itoken)
        if rc != 0:
            raise BoardError(f"commenting on #{number} failed: {err.strip() or 'gh exit ' + str(rc)}")


def sync(board: Board, event: str, pr: int, title: str, sha: str, dry: bool) -> list[str]:
    prefix = "DRY " if dry else ""
    lines: list[str] = []
    for n in parse_numbers(title, pr):
        issue = board.issue(n)
        if issue is None:
            lines.append(f"{prefix}#{n} not found: ignored")
            continue
        if "pull_request" in issue:
            lines.append(f"{prefix}#{n} pull request: ignored")
            continue
        labels = [(lb.get("name") if isinstance(lb, dict) else lb) for lb in issue.get("labels", [])]
        if "type:epic" in labels:
            lines.append(f"{prefix}#{n} epic: ignored")
            continue
        item = board.items.get(n)
        if item is None:
            lines.append(f"{prefix}#{n} not on board: ignored")
            continue
        stage = field_value(item, STAGE_FIELD)
        target = decide(event, stage)
        if target is None:
            lines.append(f"{prefix}#{n} {stage or '(no Stage)'}: unchanged")
            continue
        line = f"{prefix}#{n} {stage or '(no Stage)'} -> {target}"
        if not dry:
            board.set_stage(item, target)
        if event == "merged":
            if board.has_comment(n, pr):
                line += " (comment exists)"
            else:
                line += " (comment posted)" if not dry else " (comment would be posted)"
                if not dry:
                    board.post_comment(n, comment_text(pr, title, sha))
        lines.append(line)
    return lines


def main(argv: list[str] | None = None, run: Runner = real_runner, environ: dict | None = None) -> int:
    env = os.environ if environ is None else environ
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--event", required=True, choices=["opened", "merged"])
    parser.add_argument("--pr", required=True, type=int)
    parser.add_argument("--title", required=True)
    parser.add_argument("--sha", default="")
    parser.add_argument("--repo", default=env.get("GITHUB_REPOSITORY") or DEFAULT_REPO)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)

    token = env.get("GH_TOKEN", "")
    if not token:
        print(SKIP_MESSAGE)
        return 0
    board = Board(run, args.repo, token, env.get("ISSUE_TOKEN") or token)
    try:
        board.load()
        for line in sync(board, args.event, args.pr, args.title, args.sha, args.dry_run):
            print(line)
    except BoardError as exc:
        print(f"board sync failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
