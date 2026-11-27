# Author:    mikomeller
# Version:   0.1.1
# Filename:  test_board_sync.py
# Pathname:  tests/test_board_sync.py
# Purpose:   Unit tests of scripts/board_sync.py with a fake gh runner: title parsing, decision table,
#            idempotent exact-marker comment, repository filter, no title in the comment,
#            missing token, API failure, dry-run without writes (no network)
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

    def __init__(self, issues: dict, comments: dict | None = None, fail: str | None = None,
                 repo: str = bs.DEFAULT_REPO, limit_items: int | None = None):
        self.issues, self.comments, self.fail = issues, comments or {}, fail
        self.repo, self.limit_items = repo, limit_items

        self.calls: list[tuple[list[str], str | None]] = []

    def bodies(self, n: int) -> list[str]:
        return [c["body"] for c in self.comments.get(n, [])]

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
                    content = {"number": n, "repository": d.get("repo", self.repo)}
                    item = {"id": f"item{n}", "content": content}
                    if d.get("stage"):
                        item["stage"] = d["stage"]
                    items.append(item)
            if self.limit_items:
                items = (items * self.limit_items)[: self.limit_items]
            return 0, json.dumps({"items": items}), ""
        if args[:2] == ["project", "item-edit"]:
            n = int(args[args.index("--id") + 1][len("item"):])
            self.issues[n]["stage"] = args[args.index("--single-select-option-id") + 1][len("opt-"):]
            return 0, "", ""
        if args[0] == "api" and "POST" in args:
            n = int(args[3].split("/")[4])
            self.comments.setdefault(n, []).append(
                {"login": "github-actions[bot]", "type": "Bot", "body": args[-1][len("body="):]})
            return 0, "{}", ""
        if args[0] == "api" and args[1] == "--paginate":
            n = int(args[2].split("/")[4])
            rows = [json.dumps([c["login"], c["type"], c["body"]]) for c in self.comments.get(n, [])]
            return 0, "\n".join(rows), ""
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
        "#5 In progress -> Test (comment posted)", "#6 Test: unchanged (comment posted)",
        "#7 Demo-ready: unchanged", "#30 epic: ignored"]
    assert set(fake.comments) == {1, 3, 5, 6}
    assert fake.bodies(3) == [
        "Moved to Test by the board automation: pull request #99 was merged (abcdef1).\n"
        "<!-- board-sync pr=99 -->"]
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
    rc = run_main(fake, "--event", "merged", "--pr", "99", "--title", "x (#3)")
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


def merged(fake, title="x (#3)", pr="9", sha="abc1234567"):
    return run_main(fake, "--event", "merged", "--pr", pr, "--title", title, "--sha", sha)


def user_comment(body: str) -> dict:
    return {"login": "someone", "type": "User", "body": body}


def test_marker_collision_pr9_vs_pr99():
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}},
                  comments={3: [{"login": "github-actions[bot]", "type": "Bot",
                                 "body": "Moved.\n<!-- board-sync pr=99 -->"}]})
    assert merged(fake, pr="9") == 0
    assert len(fake.comments[3]) == 2
    assert "pr=9 -->" in fake.bodies(3)[1]


def test_user_posted_marker_does_not_suppress_bot_comment():
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}},
                  comments={3: [user_comment("<!-- board-sync pr=9 -->")]})
    assert merged(fake) == 0
    assert len(fake.comments[3]) == 2
    assert fake.comments[3][1]["login"] == "github-actions[bot]"


def test_comment_contains_no_title_text():
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}})
    title = "hi @someone [click](http://evil.example) (#3)"
    assert merged(fake, title=title) == 0
    body = fake.bodies(3)[0]
    for part in ("@someone", "evil.example", "[click]", "hi"):
        assert part not in body.replace("this", "")


def test_item_from_other_repository_is_ignored(capsys):
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog", "repo": "other/repo"}})
    assert merged(fake) == 0
    assert capsys.readouterr().out.strip() == "#3 not on board: ignored"
    assert fake.writes() == []


def test_not_on_board(capsys):
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}, 5: {"kind": "pr"}})
    del fake.issues[3]["kind"]
    fake.issues[3]["kind"] = "issue"
    fake.issues[8] = {"kind": "issue", "stage": "Ready"}
    orig = fake.__call__

    def hide(args, token):
        rc, out, err = orig(args, token)
        if args[:2] == ["project", "item-list"]:
            out = json.dumps({"items": [i for i in json.loads(out)["items"] if i["content"]["number"] != 8]})
        return rc, out, err
    assert bs.main(["--event", "opened", "--pr", "1", "--title", "x (#8)"], run=hide, environ=ENV) == 0
    assert capsys.readouterr().out.strip() == "#8 not on board: ignored"


def test_comment_post_failure_moves_card_exit_1_and_rerun_posts(capsys):
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}}, fail="POST")
    assert merged(fake) == 1
    captured = capsys.readouterr()
    assert "commenting on #3 failed" in captured.err and "board sync failed" in captured.err
    assert fake.issues[3]["stage"] == "Test" and not fake.comments
    fake.fail = None
    assert merged(fake) == 0
    assert len(fake.comments[3]) == 1
    assert merged(fake) == 0
    assert len(fake.comments[3]) == 1


def test_card_in_test_without_marker_gets_comment_demo_ready_never():
    fake = FakeGh({3: {"kind": "issue", "stage": "Test"}, 4: {"kind": "issue", "stage": "Demo-ready"}})
    assert merged(fake, title="x (#3, #4)") == 0
    assert len(fake.comments[3]) == 1 and 4 not in fake.comments
    assert fake.writes() == [a for a, _ in fake.calls if "POST" in a]  # no card move


def test_opened_event_never_comments_on_test_card():
    fake = FakeGh({3: {"kind": "issue", "stage": "Test"}})
    assert run_main(fake, "--event", "opened", "--pr", "9", "--title", "x (#3)") == 0
    assert not fake.comments


def test_option_shaped_title_is_a_title(capsys):
    fake = FakeGh({5: {"kind": "issue", "stage": "Backlog"}})
    rc = run_main(fake, "--event=opened", "--pr=9", "--title=--dry-run (#5)")
    assert rc == 0
    assert capsys.readouterr().out.strip() == "#5 Backlog -> In progress"  # not a dry run
    assert fake.issues[5]["stage"] == "In progress"


def test_pagination_warning(capsys):
    fake = FakeGh({3: {"kind": "issue", "stage": "Backlog"}}, limit_items=bs.ITEM_LIMIT)
    assert run_main(fake, "--dry-run", "--event", "opened", "--pr", "9", "--title", "x (#3)") == 0
    out = capsys.readouterr().out.splitlines()
    assert out[0] == f"warning: project has {bs.ITEM_LIMIT}+ items; raise the limit"
    assert out[1] == "DRY #3 Backlog -> In progress"
