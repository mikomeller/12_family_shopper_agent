#!/usr/bin/env python3
# Author:    mikomeller
# Version:   0.1.0
# Filename:  seed_wallet.py
# Pathname:  scripts/seed_wallet.py
# Purpose:   Create/reset the demo wallet SQLite (WALLET_DB or data/wallet.sqlite) from the budget config; optionally print member tokens
"""Reset the wallet DB to a known demo state. Deletes only the SQLite file it owns (plus -wal/-shm)."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from family_shopper.wallet import db  # noqa: E402
from family_shopper.wallet.identity import mint_token  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print-tokens", action="store_true", help="print a signed token per member")
    ap.add_argument("--ttl", type=int, default=86400, help="token lifetime in seconds (default 1 day)")
    ap.add_argument(
        "--config", default=None, help="budget YAML (default: config/family_budget[.example].yaml)"
    )
    args = ap.parse_args()

    path = db.default_db_path()
    for suffix in ("", "-wal", "-shm"):
        Path(f"{path}{suffix}").unlink(missing_ok=True)
    config = db.load_config(args.config)
    conn = db.connect(path)
    try:
        db.init_db(conn, config)
    finally:
        conn.close()
    print(f"Seeded {path}: family cap {config['family_cap_cents']} cents")
    for m in config["members"]:
        print(f"  {m['id']:<10} {m['role']:<7} personal cap {m['personal_cap_cents']}")
    if args.print_tokens:
        secret = os.environ.get("WALLET_TOKEN_SECRET", "")
        if not secret:
            print("WALLET_TOKEN_SECRET is not set; cannot mint tokens.", file=sys.stderr)
            return 1
        for m in config["members"]:
            print(f"WALLET_MEMBER_TOKEN[{m['id']}]={mint_token(m['id'], args.ttl, secret)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
