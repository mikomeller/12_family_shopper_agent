#!/usr/bin/env python3
"""
Author:    mikomeller
Version:   0.1.0
Filename:  create_collaborator_branches.py
Pathname:  scripts/create_collaborator_branches.py
Purpose:   Creates one branch per collaborator of mikomeller/12_family_shopper_agent, named after the
           collaborator's GitHub login. Covers accepted collaborators AND pending invitations; the owner
           is skipped. Branches start from the current tip of 'main'. 'main' itself is never written:
           it stays reserved for reviewed code (merge via pull requests).
           Re-runnable: existing branches are left untouched; run again after new people are invited.
Usage:     python3 scripts/create_collaborator_branches.py --dry-run   # read GitHub, show plan, create nothing
           python3 scripts/create_collaborator_branches.py             # create the missing branches
"""
from __future__ import annotations

import argparse
import json
import re
import shlex
import shutil
import subprocess
import sys

OWNER = "mikomeller"
REPO = "12_family_shopper_agent"
FULL_REPO = f"{OWNER}/{REPO}"
BASE_BRANCH = "main"


def gh_api(path: str, *fields: str, paginate: bool = False):
    """Call 'gh api'. With fields it POSTs; otherwise it GETs and returns parsed JSON."""
    cmd = ["gh", "api", path]
    if paginate:
        cmd += ["--paginate", "--slurp"]
    for f in fields:
        cmd += ["-f", f]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"FAILED: {shlex.join(cmd)}\n{res.stderr.strip()}")
    data = json.loads(res.stdout) if res.stdout.strip() else None
    if paginate and data is not None:  # --slurp wraps pages in an outer list
        data = [item for page in data for item in page]
    return data


def branch_name(login: str) -> str:
    """Git-safe branch name from a GitHub login (logins are already alphanumeric + '-')."""
    return re.sub(r"[^A-Za-z0-9._-]", "-", login)


def collect_people() -> dict[str, str]:
    """Return {login: status} for collaborators and pending invitees, owner excluded."""
    people: dict[str, str] = {}
    for c in gh_api(f"repos/{FULL_REPO}/collaborators?per_page=100", paginate=True) or []:
        people[c["login"]] = "collaborator"
    for inv in gh_api(f"repos/{FULL_REPO}/invitations?per_page=100", paginate=True) or []:
        invitee = inv.get("invitee")
        if invitee and invitee.get("login"):
            people.setdefault(invitee["login"], "invited (pending)")
        else:
            print(f"  skipped invitation #{inv.get('id')}: invited by e-mail, no GitHub login yet")
    people.pop(OWNER, None)
    return people


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="read GitHub and print the plan; create nothing")
    args = parser.parse_args()

    if not shutil.which("gh"):
        sys.exit("'gh' not found. Install it: brew install gh")

    base_sha = gh_api(f"repos/{FULL_REPO}/git/ref/heads/{BASE_BRANCH}")["object"]["sha"]
    print(f"Base: {BASE_BRANCH} @ {base_sha[:7]} (main is only read, never changed)")

    people = collect_people()
    if not people:
        print("No collaborators or pending invitations found (besides the owner). Nothing to do.")
        return

    existing = {b["name"] for b in gh_api(f"repos/{FULL_REPO}/branches?per_page=100", paginate=True) or []}
    created = 0
    for login, status in sorted(people.items(), key=lambda kv: kv[0].lower()):
        name = branch_name(login)
        if name == BASE_BRANCH:
            print(f"  {login:<25} skipped: would collide with '{BASE_BRANCH}'")
        elif name in existing:
            print(f"  {login:<25} {status:<18} branch '{name}' already exists")
        elif args.dry_run:
            print(f"  {login:<25} {status:<18} would create branch '{name}'")
        else:
            gh_api(f"repos/{FULL_REPO}/git/refs", f"ref=refs/heads/{name}", f"sha={base_sha}")
            print(f"  {login:<25} {status:<18} created branch '{name}'")
            created += 1
    print(f"\n{'Dry run - nothing created.' if args.dry_run else f'Branches created: {created}'}")


if __name__ == "__main__":
    main()
