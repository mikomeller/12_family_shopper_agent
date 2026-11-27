#!/usr/bin/env python3
# Author:    mikomeller
# Version:   0.1.0
# Filename:  wallet_tokens.py
# Pathname:  scripts/wallet_tokens.py
# Purpose:   Print JSON {member_id: signed token} for all members in the wallet db (creates the db only if missing; never resets)
"""Print one signed wallet token per member. Secret from WALLET_TOKEN_SECRET, db from WALLET_DB."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from family_shopper.wallet import db  # noqa: E402
from family_shopper.wallet.identity import mint_token  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--ttl", type=int, default=86400, help="token lifetime in seconds (default 1 day)")
    args = ap.parse_args()

    secret = os.environ.get("WALLET_TOKEN_SECRET", "")
    if not secret:
        print("WALLET_TOKEN_SECRET is not set; cannot mint tokens.", file=sys.stderr)
        return 1
    path = db.default_db_path()
    conn = db.connect(path)
    try:
        if not Path(path).exists() or not conn.execute(
            "SELECT name FROM sqlite_master WHERE name = 'members'"
        ).fetchone():
            db.init_db(conn, db.load_config())
        ids = [r["id"] for r in conn.execute("SELECT id FROM members ORDER BY id")]
    finally:
        conn.close()
    print(json.dumps({m: mint_token(m, args.ttl, secret) for m in ids}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
