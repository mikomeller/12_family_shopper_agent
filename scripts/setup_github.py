#!/usr/bin/env python3
"""
Author:    mikomeller
Version:   0.1.2
Filename:  setup_github.py
Pathname:  scripts/setup_github.py
Purpose:   One-shot, re-runnable GitHub setup for 12_family_shopper_agent, run on your Mac:
             1. local git repo + first commit (if missing)
             2. private GitHub repo mikomeller/12_family_shopper_agent (if missing) + push
             3. labels and milestones
             4. user Project "12_family_shopper_agent" (found or created) + custom fields
             5. backlog issues from backlog.json, added to the Project with field values
             6. epic -> story links: an issue with "parent" becomes a sub-issue of that epic
           Existing repo, labels, milestones, fields and issues are reused, never deleted.
           Field values (Stage, Priority, ...) are set only on issues created in this run,
           so a re-run never moves cards the team has already moved on the board.
Usage:     gh auth login                     # once, if gh is not logged in
           gh auth refresh -s project        # once, adds the Projects scope
           python3 scripts/setup_github.py --dry-run   # offline: validate + print every command
           python3 scripts/setup_github.py             # run it
"""
from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import time
from pathlib import Path

OWNER = "mikomeller"
REPO = "12_family_shopper_agent"
PROJECT_TITLE = "12_family_shopper_agent"
FULL_REPO = f"{OWNER}/{REPO}"
DESCRIPTION = ("Family shopping agent on TrustBoris + idealo MCP with individual and "
               "family spending caps (AI Agents Berlin hackathon)")
ROOT = Path(__file__).resolve().parent.parent
BACKLOG_FILE = Path(__file__).resolve().parent / "backlog.json"


class CmdError(RuntimeError):
    """A gh or git command failed."""


class Runner:
    """Runs gh/git commands. In dry-run mode it only prints them and returns empty output."""

    def __init__(self, dry_run: bool) -> None:
        self.dry_run = dry_run

    def run(self, tool: str, args: list[str], check: bool = True) -> subprocess.CompletedProcess:
        cmd = [tool, *args]
        if self.dry_run:
            print("  $", shlex.join(cmd))
            return subprocess.CompletedProcess(cmd, 0, "", "")
        res = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)
        if check and res.returncode != 0:
            raise CmdError(f"{shlex.join(cmd)}\n{res.stderr.strip()}")
        return res

    def ok(self, tool: str, args: list[str]) -> bool:
        """True if the command succeeds. Read-only probe; in dry-run assume 'not there yet'."""
        if self.dry_run:
            return False
        return subprocess.run([tool, *args], cwd=ROOT, capture_output=True, text=True).returncode == 0

    def gh(self, args: list[str]) -> str:
        return self.run("gh", args).stdout.strip()

    def gh_json(self, args: list[str]):
        out = self.gh(args)
        return json.loads(out) if out else None


# ---------------------------------------------------------------- backlog

def load_backlog(path: Path) -> dict:
    """Load backlog.json and check every label, milestone and field value it references."""
    data = json.loads(path.read_text(encoding="utf-8"))
    labels = {label["name"] for label in data["labels"]}
    milestones = {m["title"] for m in data["milestones"]}
    fields = data["fields"]
    errors, titles = [], set()
    for issue in data["issues"]:
        title = issue["title"]
        if title in titles:
            errors.append(f"duplicate title: {title}")
        titles.add(title)
        errors += [f"{title}: unknown label '{lb}'" for lb in issue.get("labels", []) if lb not in labels]
        if issue.get("milestone") and issue["milestone"] not in milestones:
            errors.append(f"{title}: unknown milestone '{issue['milestone']}'")
        if issue.get("parent") and issue["parent"] not in {i["title"] for i in data["issues"]}:
            errors.append(f"{title}: unknown parent '{issue['parent']}'")
        if issue.get("parent") == title:
            errors.append(f"{title}: is its own parent")
        for name, value in issue.get("fields", {}).items():
            if name not in fields:
                errors.append(f"{title}: unknown field '{name}'")
            elif value not in fields[name]:
                errors.append(f"{title}: '{value}' is not an option of field '{name}'")
    if errors:
        sys.exit("backlog.json is invalid:\n  " + "\n  ".join(errors))
    return data


# ---------------------------------------------------------------- steps

def check_prereqs(r: Runner) -> None:
    if r.dry_run:
        return
    for tool, hint in (("git", "xcode-select --install"), ("gh", "brew install gh")):
        if not shutil.which(tool):
            sys.exit(f"'{tool}' not found. Install it: {hint}")
    if not r.ok("gh", ["auth", "status"]):
        sys.exit("gh is not logged in. Run: gh auth login && gh auth refresh -s project")


def ensure_local_git(r: Runner) -> None:
    print("[1/7] Local git repository")
    if not (ROOT / ".git").exists():
        r.run("git", ["init", "-b", "main"])
    if not r.ok("git", ["rev-parse", "--verify", "HEAD"]):
        r.run("git", ["add", "-A"])
        r.run("git", ["commit", "-m", "chore: initial scaffold v0.1.0"])
        print("  first commit created")
    else:
        print("  already has commits")


def ensure_repo(r: Runner) -> None:
    """Create the GitHub repo if missing, make sure 'origin' exists, push if the branch has no upstream.
    gh's own --source/--remote/--push handling is not used: if it fails half-way (repo created, push
    skipped) a re-run could not recover."""
    print(f"[2/7] GitHub repository {FULL_REPO}")
    if r.ok("gh", ["repo", "view", FULL_REPO, "--json", "name"]):
        print("  exists")
    else:
        r.run("gh", ["repo", "create", FULL_REPO, "--private", "--description", DESCRIPTION])
        print("  created (private)")
    if not r.ok("git", ["remote", "get-url", "origin"]):
        r.run("git", ["remote", "add", "origin", f"https://github.com/{FULL_REPO}.git"])
        print("  remote 'origin' added")
    if r.ok("git", ["rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{u}"]):
        print("  branch already tracks a remote branch; push skipped")
        return
    r.run("git", ["push", "-u", "origin", "HEAD"])
    print("  pushed")


def ensure_labels_and_milestones(r: Runner, labels: list[dict], milestones: list[dict]) -> None:
    print("[3/7] Labels and milestones")
    for lb in labels:
        r.gh(["label", "create", lb["name"], "--color", lb["color"], "--description",
              lb["description"], "--force", "-R", FULL_REPO])
    existing = r.gh_json(["api", f"repos/{FULL_REPO}/milestones?state=all&per_page=100"]) or []
    have = {m["title"] for m in existing}
    for m in milestones:
        if m["title"] not in have:
            r.gh(["api", f"repos/{FULL_REPO}/milestones", "-f", f"title={m['title']}",
                  "-f", f"description={m['description']}"])
    print(f"  {len(labels)} labels, {len(milestones)} milestones ensured")


def ensure_project(r: Runner, number: str | None) -> tuple[str, str]:
    print(f"[4/7] Project '{PROJECT_TITLE}'")
    listing = r.gh_json(["project", "list", "--owner", OWNER, "--format", "json", "--limit", "100"])
    projects = (listing or {}).get("projects", [])
    match = next((p for p in projects
                  if (number and str(p["number"]) == number) or (not number and p["title"] == PROJECT_TITLE)),
                 None)
    if match:
        num, pid = str(match["number"]), match["id"]
        print(f"  found #{num}")
    elif number and not r.dry_run:
        sys.exit(f"  project #{number} not found for {OWNER}")
    else:
        created = r.gh_json(["project", "create", "--owner", OWNER, "--title", PROJECT_TITLE, "--format", "json"])
        num, pid = (str(created["number"]), created["id"]) if created else ("<N>", "<PROJECT_ID>")
        print(f"  created #{num}")
    res = r.run("gh", ["project", "link", num, "--owner", OWNER, "--repo", FULL_REPO], check=False)
    if res.returncode != 0:
        print(f"  link to repo skipped: {res.stderr.strip().splitlines()[-1] if res.stderr.strip() else 'unknown'}")
    return num, pid


def ensure_fields(r: Runner, num: str, wanted: dict[str, list[str]]) -> dict:
    print("[5/7] Project fields")

    def current() -> dict:
        data = r.gh_json(["project", "field-list", num, "--owner", OWNER, "--format", "json", "--limit", "100"])
        return {f["name"]: f for f in (data or {}).get("fields", [])}

    have = current()
    for name, options in wanted.items():
        if name in have:
            missing = set(options) - {o["name"] for o in have[name].get("options", [])}
            if missing:
                print(f"  WARNING field '{name}' exists but lacks options {sorted(missing)}; add them in the UI")
            continue
        r.gh(["project", "field-create", num, "--owner", OWNER, "--name", name,
              "--data-type", "SINGLE_SELECT", "--single-select-options", ",".join(options)])
    return current()


def ensure_issues(r: Runner, num: str, pid: str, issues: list[dict], fields: dict) -> dict[str, str]:
    """Create missing issues and add them to the Project. Returns title -> issue URL."""
    print("[6/7] Issues -> Project")
    existing = r.gh_json(["issue", "list", "-R", FULL_REPO, "--state", "all", "--limit", "500",
                          "--json", "title,url"]) or []
    by_title = {i["title"]: i["url"] for i in existing}
    created = reused = 0
    for issue in issues:
        url = by_title.get(issue["title"])
        is_new = url is None
        if url:
            reused += 1
        else:
            args = ["issue", "create", "-R", FULL_REPO, "--title", issue["title"], "--body", issue["body"]]
            for lb in issue.get("labels", []):
                args += ["--label", lb]
            if issue.get("milestone"):
                args += ["--milestone", issue["milestone"]]
            out = r.gh(args)
            url = out.splitlines()[-1] if out else f"<URL of '{issue['title']}'>"
            by_title[issue["title"]] = url
            created += 1
            if not r.dry_run:
                time.sleep(1)  # stay well below GitHub's content-creation rate limit
        item = r.gh_json(["project", "item-add", num, "--owner", OWNER, "--url", url, "--format", "json"])
        item_id = item["id"] if item else "<ITEM_ID>"
        if not is_new:
            continue  # keep the Stage/Priority the team set on the board
        for name, value in issue.get("fields", {}).items():
            if r.dry_run:
                field_id, option_id = f"<{name}>", f"<{value}>"
            else:
                field = fields.get(name)
                option_id = next((o["id"] for o in (field or {}).get("options", []) if o["name"] == value), None)
                if not field or not option_id:
                    print(f"  WARNING '{issue['title']}': cannot set {name}={value}")
                    continue
                field_id = field["id"]
            r.gh(["project", "item-edit", "--id", item_id, "--project-id", pid,
                  "--field-id", field_id, "--single-select-option-id", option_id])
    print(f"  issues created: {created}, reused: {reused}")
    return by_title


def ensure_hierarchy(r: Runner, issues: list[dict], urls: dict[str, str]) -> None:
    """Link every issue that names a 'parent' as a sub-issue of that epic (GitHub sub-issues REST API).
    Already linked children are skipped; a failed link is reported and does not stop the run."""
    print("[7/7] Epic -> story links (sub-issues)")
    api = f"repos/{FULL_REPO}/issues"

    def number(title: str) -> str:
        url = urls.get(title, "")
        tail = url.rstrip("/").rsplit("/", 1)[-1]
        return tail if tail.isdigit() else f"<number of '{title}'>"

    linked = skipped = failed = 0
    children_of: dict[str, set[str]] = {}
    for issue in issues:
        parent = issue.get("parent")
        if not parent:
            continue
        p_no, c_no = number(parent), number(issue["title"])
        if r.dry_run:
            print("  $", f"gh api -X POST {api}/{p_no}/sub_issues -F sub_issue_id=<id of #{c_no}>")
            linked += 1
            continue
        if p_no not in children_of:
            res = r.run("gh", ["api", "--paginate", f"{api}/{p_no}/sub_issues?per_page=100",
                               "--jq", ".[].number"], check=False)
            children_of[p_no] = set(res.stdout.split()) if res.returncode == 0 else set()
        if c_no in children_of[p_no]:
            skipped += 1
            continue
        child_id = r.gh(["api", f"{api}/{c_no}", "--jq", ".id"])
        res = r.run("gh", ["api", "-X", "POST", f"{api}/{p_no}/sub_issues", "-F", f"sub_issue_id={child_id}"],
                    check=False)
        if res.returncode == 0:
            linked += 1
        else:
            failed += 1
            reason = res.stderr.strip().splitlines()[-1] if res.stderr.strip() else "unknown"
            print(f"  WARNING could not link #{c_no} under #{p_no}: {reason}")
    print(f"  linked: {linked}, already linked: {skipped}, failed: {failed}")
    if failed:
        print("  Failed links can be added by hand: open the epic -> 'Create sub-issue' menu -> 'Add existing issue'.")


# ---------------------------------------------------------------- main

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="validate backlog and print commands, no network")
    parser.add_argument("--project-number", help="use this existing Project number instead of finding by title")
    args = parser.parse_args()

    backlog = load_backlog(BACKLOG_FILE)
    print(f"backlog.json OK: {len(backlog['issues'])} issues, {len(backlog['labels'])} labels, "
          f"{len(backlog['fields'])} fields{'  (DRY RUN)' if args.dry_run else ''}")
    r = Runner(args.dry_run)
    try:
        check_prereqs(r)
        ensure_local_git(r)
        ensure_repo(r)
        ensure_labels_and_milestones(r, backlog["labels"], backlog["milestones"])
        num, pid = ensure_project(r, args.project_number)
        fields = ensure_fields(r, num, backlog["fields"])
        urls = ensure_issues(r, num, pid, backlog["issues"], fields)
        ensure_hierarchy(r, backlog["issues"], urls)
    except CmdError as exc:
        sys.exit(f"\nFAILED:\n{exc}\nFix the cause and re-run; finished steps are skipped.")
    print(f"\nDone. Repo: https://github.com/{FULL_REPO}  Project: https://github.com/users/{OWNER}/projects/{num}")
    print("Last manual step: in the Project add a Board view and set 'Column by' = Stage.")


if __name__ == "__main__":
    main()
