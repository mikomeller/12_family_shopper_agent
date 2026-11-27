#!/usr/bin/env python3
"""
Author:    mikomeller
Version:   0.1.0
Filename:  board.py
Pathname:  scripts/board.py
Purpose:   Read and move cards on the GitHub Project "12_family_shopper_agent" through the gh CLI,
           so the orchestrator (and people) can work from the Kanban board in a terminal.
Usage:     python3 scripts/board.py list                      # all cards, grouped by Stage
           python3 scripts/board.py list --stage Ready        # one column
           python3 scripts/board.py move 12 "In progress"     # move issue #12 to a Stage
           Needs: gh auth login && gh auth refresh -s project
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys

OWNER = "mikomeller"
PROJECT_TITLE = "12_family_shopper_agent"
STAGE_FIELD = "Stage"
PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2}


def gh(args: list[str]) -> str:
    res = subprocess.run(["gh", *args], capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"gh {' '.join(args)}\n{res.stderr.strip()}")
    return res.stdout.strip()


def gh_json(args: list[str]):
    out = gh(args)
    return json.loads(out) if out else {}


def find_project(number: str | None) -> dict:
    projects = gh_json(["project", "list", "--owner", OWNER, "--format", "json", "--limit", "100"]).get("projects", [])
    for p in projects:
        if (number and str(p["number"]) == number) or (not number and p["title"] == PROJECT_TITLE):
            return p
    sys.exit(f"Project not found for {OWNER} (title '{PROJECT_TITLE}', number {number or 'auto'}).")


def field_value(item: dict, name: str) -> str:
    """gh prints custom fields as top-level keys; match the name case-insensitively."""
    for key, value in item.items():
        if key.lower() == name.lower() and isinstance(value, str):
            return value
    return ""


def load_items(num: str) -> list[dict]:
    return gh_json(["project", "item-list", num, "--owner", OWNER, "--format", "json", "--limit", "500"]).get("items", [])


def cmd_list(num: str, stage: str | None, stages: list[str]) -> None:
    items = [i for i in load_items(num) if i.get("content", {}).get("number")]
    if stage:
        stages = [s for s in stages if s.lower() == stage.lower()] or sys.exit(f"Unknown stage '{stage}'. Use one of: {stages}")
    for s in stages:
        cards = [i for i in items if field_value(i, STAGE_FIELD) == s]
        cards.sort(key=lambda i: (PRIORITY_ORDER.get(field_value(i, "Priority"), 9), i["content"]["number"]))
        print(f"\n## {s} ({len(cards)})")
        for i in cards:
            kind = "EPIC " if "type:epic" in (i.get("labels") or []) else ""
            print(f"  #{i['content']['number']:<4} {field_value(i, 'Priority') or '--':<3} "
                  f"{field_value(i, 'Size') or '-':<2} {kind}{i['content']['title']}")
    unstaged = [i for i in items if not field_value(i, STAGE_FIELD)]
    if unstaged and not stage:
        print(f"\n## (no Stage) ({len(unstaged)})")
        for i in unstaged:
            print(f"  #{i['content']['number']:<4} {i['content']['title']}")


def cmd_move(project: dict, issue_number: int, stage: str, field: dict) -> None:
    option = next((o for o in field.get("options", []) if o["name"].lower() == stage.lower()), None)
    if not option:
        sys.exit(f"Unknown stage '{stage}'. Use one of: {[o['name'] for o in field.get('options', [])]}")
    item = next((i for i in load_items(str(project["number"])) if i.get("content", {}).get("number") == issue_number), None)
    if not item:
        sys.exit(f"Issue #{issue_number} is not on the board.")
    before = field_value(item, STAGE_FIELD) or "(none)"
    gh(["project", "item-edit", "--id", item["id"], "--project-id", project["id"],
        "--field-id", field["id"], "--single-select-option-id", option["id"]])
    print(f"#{issue_number} {item['content']['title']}: {before} -> {option['name']}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--project-number", help="use this Project number instead of finding it by title")
    sub = parser.add_subparsers(dest="cmd", required=True)
    p_list = sub.add_parser("list", help="show cards grouped by Stage")
    p_list.add_argument("--stage")
    p_move = sub.add_parser("move", help="move an issue to a Stage")
    p_move.add_argument("issue", type=int)
    p_move.add_argument("stage")
    args = parser.parse_args()

    project = find_project(args.project_number)
    num = str(project["number"])
    fields = gh_json(["project", "field-list", num, "--owner", OWNER, "--format", "json", "--limit", "100"]).get("fields", [])
    field = next((f for f in fields if f["name"] == STAGE_FIELD), None)
    if not field:
        sys.exit(f"Field '{STAGE_FIELD}' not found on the Project. Run scripts/setup_github.py first.")
    if args.cmd == "list":
        cmd_list(num, args.stage, [o["name"] for o in field.get("options", [])])
    else:
        cmd_move(project, args.issue, args.stage, field)


if __name__ == "__main__":
    main()
