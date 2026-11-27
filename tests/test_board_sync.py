# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_board_sync.py
# Pathname:  tests/test_board_sync.py
# Purpose:   Unit tests of scripts/board_sync.py with a fake gh runner: title parsing, decision table,
#            idempotent comment, missing token, API failure, dry-run without writes (no network)
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import board_sync as bs  # noqa: E402

STAGES = ["Ideas", "Backlog", "Ready", "In progress", "Test", "Demo-ready"]
OPTIONS = [{"id": f"opt-{s}", "name": s} for s in STAGES]


class FakeGh:
    """Stands in for the gh CLI. issues: number -> dict(kind, labels, stage)."""

    def __init__(self, issues: dict, comments: dict | None = None, fail: str | None = None):
        self.issues, self.comments, self.fail = issues, comments or {}, fail
        self.calls: list[tuple[list[str], str | None]] = []

    def writes(self) -> list[list[str]]:
        return [a for a, _ in self.calls if "item-edit" in a or "POST" in a]

    def __call__(self, args: list[str], token: str | None):
        self.calls.append((args, token))
        if self.fail and self.fail in " ".join(args):
            return 1, "", "HTTP 500 boom"
        if args[:2] == ["project", "list"]:
            return 0, json.dumps({"projects": [{"title": bs.PROJECT_TITLE, "number": 1, "id": "P"}]}), ""
        if args[:2] == ["project", "field-list"]:
            return 0, json.dumps({"fields": [{"name": "Stage", "id": "F", "options": OPTIONS}]}), ""
        if args[:2] == ["project", "item-list"]:
            items = []
            for n, d in self.issues.items():
                if d["kind"] == "issue":
                    item = {"id": f"item{n}", "content": {"number": n}}
                    if d.get("stage"):
                        item["stage"] = d["stage"]
                    items.append(item)
            return 0, json.dumps({"items": items}), ""
        if args[:2] == ["project", "item-edit"]:
            return 0, "", ""
        if args[0] == "api" and "POST" in args:
            n = int(args[3].split("/")[4])
            self.comments.setdefault(n, []).append(args[-1][len("body="):])
            return 0, "{}", ""
        if args[0] == "api" and args[1] == "--paginate":
            n = int(args[2].split("/")[4])
            return 0, "\n".join(self.comments.get(n, [])), ""
        if args[0] == "api":
            n = int(args[1].split("/")[4])
            d = self.issues.get(n)
            if d is None:
                return 1, "", "gh: Not Found (HTTP 404)"
            body = {"number": n, "labels": [{"name": x} for x in d.get("labels", [])]}
            if d["kind"] == "pr":
                body["pull_request"] = {}
            return 0, json.dumps(body), ""
        raise AssertionError(args)


ENV = {"GH_TOKEN": "tok", "ISSUE_TOKEN": "itok"}


def run_main(fake: FakeGh, *argv: str, env: dict | None = None) -> int:
    return bs.main(list(argv), run=fake, environ=ENV if env is None else env)


@pytest.mark.parametrize("title,expected", [
    ("feat: wallet server (#7, #8)", [7, 8]),
    ("fix: x (#7) (#44)", [7, 44]),
    ("chore: nothing here", []),
    ("feat: #7 in the middle of text", [7]),
    ("fix: leading zeros (#007)", [7]),
    ("fix: own number (#9) (#9)", [9]),
    ("fix: letters #7a and #x8 and # 9", [7]),
    ("$(rm -rf /) (#7); echo `id` #8", [7, 8]),
    ("x" * 300 + " (#7)", [7]),
    ("(" + ", ".join(f"#{i}" for i in range(100, 160)) + ")", list(range(100, 120))),
])
def test_parse_numbers(title, expected):
    assert bs.parse_numbers(title, own_pr=9999) == expected


def test_parse_drops_own_pr_number():
    assert bs.parse_numbers("feat: x (#7) (#12)", own_pr=12) == [7]


@pytest.mark.parametrize("stage,expected", [
    ("", None), ("Ideas", "In progress"), ("Backlog", "In progress"), ("Ready", "In progress"),
    ("In progress", None), ("Test", None), ("Demo-ready", None)])
def test_decide_opened(stage, expected):
    assert bs.decide("opened", stage) == expected


@pytest.mark.parametrize("stage,expected", [
    ("", "Test"), ("Ideas", "Test"), ("Backlog", "Test"), ("Ready", "Test"), ("In progress", "Test"),
    ("Test", None), ("Demo-ready", None)])
def test_decide_merged(stage, expected):
    assert bs.decide("merged", stage) == expected


def issues() -> dict:
    d = {n: {"kind": "issue", "stage": s} for n, s in zip(range(1, 8), [None, *STAGES], strict=True)}
    d[20] = {"kind": "pr"}
    d[30] = {"kind": "issue", "labels": ["type:epic"], "stage": "Backlog"}
    return d


def test_opened_table(capsys):
    fake = FakeGh(issues())
    title = "feat: t (#1, #2, #3, #4, #5, #6, #7, #20, #30, #404)"
    rc = run_main(fake, "--event", "opened", "--pr", "99", "--title", title)
    out = capsys.readouterr().out.splitlines()
    assert rc == 0
    assert out == [
        "#1 (no Stage): unchanged", "#2 Ideas -> In progress", "#3 Backlog -> In progress",
        "#4 Ready -> In progress",
        "#5 In progress: unchanged", "#6 Test: unchanged", "#7 Demo-ready: unchanged",
        "#20 pull request: ignored", "#30 epic: ignored", "#404 not found: ignored"]
    assert len(fake.writes()) == 3
    assert not fake.comments


def test_merged_table_and_comment(capsys):
    fake = FakeGh(issues())
    rc = run_main(fake, "--event", "merged", "--pr", "99", "--title", 'feat: "t" (#1, #3, #5, #6, #7, #30)',
                  "--sha", "abcdef1234567")
    out = capsys.readouterr().out.splitlines()
    assert rc == 0
    assert out == [
        "#1 (no Stage) -> Test (comment posted)", "#3 Backlog -> Test (comment posted)",
        "#5 In progress -> Test (comment posted)", "#6 Test: unchanged", "#7 Demo-ready: unchanged",
        "#30 epic: ignored"]
    assert set(fake.comments) == {1, 3, 5}
    assert fake.comments[3] == [
        'Moved to Test by the board automation: pull request #99 "feat: "t" (#1, #3, #5, #6, #7, #30)"'
        " was merged (abcdef1)."]
    # the comment goes out with the issue token, the board write with the project token
    assert any(t == "itok" for a, t in fake.calls if "POST" in a)
    assert all(t == "tok" for a, t in fake.calls if "item-edit" in a)


def test_merged_comment_is_idempotent(capsys):
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}})
    args = ("--event", "merged", "--pr", "99", "--title", "x (#3)", "--sha", "abc1234")
    assert run_main(fake, *args) == 0
    # a re-run after the card is already moved: unchanged, no second comment
    fake.issues[3]["stage"] = "Test"
    assert run_main(fake, *args) == 0
    assert len(fake.comments[3]) == 1
    # a card back in an earlier stage but the comment exists: moves, does not comment again
    fake.issues[3]["stage"] = "Ready"
    run_main(fake, *args)
    assert len(fake.comments[3]) == 1
    assert "(comment exists)" in capsys.readouterr().out


def test_missing_token_skips(capsys):
    fake = FakeGh(issues())
    for env in ({}, {"GH_TOKEN": ""}):
        assert run_main(fake, "--event", "merged", "--pr", "1", "--title", "x (#3)", env=env) == 0
    assert capsys.readouterr().out.count(bs.SKIP_MESSAGE) == 2
    assert fake.calls == []


@pytest.mark.parametrize("fail", ["project list", "field-list", "item-list", "item-edit", "repos/mikomeller",
                                  "comments"])
def test_api_failure_exits_1(fail, capsys):
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}}, fail=fail)
    rc = run_main(fake, "--event", "merged", "--pr", "99", "--title", "x (#3)", "--repo", "mikomeller/r")
    assert rc == 1
    assert "board sync failed" in capsys.readouterr().err


@pytest.mark.parametrize("event", ["opened", "merged"])
def test_dry_run_writes_nothing(event, capsys):
    fake = FakeGh(issues())
    rc = run_main(fake, "--dry-run", "--event", event, "--pr", "99", "--title", "x (#2, #3, #20, #30, #404)")
    out = capsys.readouterr().out.splitlines()
    assert rc == 0
    assert out and all(line.startswith("DRY ") for line in out)
    assert fake.writes() == []
    assert not fake.comments


def test_hostile_title_is_never_a_command(capsys):
    fake = FakeGh({7: {"kind": "issue", "stage": "Backlog"}})
    run_main(fake, "--dry-run", "--event", "opened", "--pr", "1", "--title", "$(rm -rf) (#7); echo")
    assert capsys.readouterr().out.strip() == "DRY #7 Backlog -> In progress"
    assert all("rm -rf" not in " ".join(a) for a, _ in fake.calls)
