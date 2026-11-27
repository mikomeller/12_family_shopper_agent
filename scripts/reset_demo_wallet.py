#!/usr/bin/env python3
# Author:    mikomeller
# Version:   0.1.0
# Filename:  reset_demo_wallet.py
# Pathname:  scripts/reset_demo_wallet.py
# Purpose:   Reset the demo wallet at WALLET_DB in one transaction: delete all orders and approval requests, restore caps from the config; keeps the db file and members
"""Touches only the db at WALLET_DB (refuses when unset). Never deletes the file; tokens stay valid (the secret is not in the db)."""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from family_shopper.wallet import db  # noqa: E402


def main() -> int:
    if not os.environ.get("WALLET_DB"):
        print("WALLET_DB is not set; refusing to reset anything.", file=sys.stderr)
        return 2
    path = db.default_db_path()
    if not Path(path).exists():
        print(f"No wallet db at {path}; nothing reset.", file=sys.stderr)
        return 2
    config = db.load_config()
    conn = db.connect(path)
    try:
        db.init_db(conn, config)  # schema + seed only if empty
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("DELETE FROM orders")
            conn.execute("DELETE FROM approval_requests")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('orders','approval_requests')")
            conn.execute("UPDATE family SET family_cap_cents = ? WHERE id = 1", (config["family_cap_cents"],))
            conn.executemany(
                "UPDATE members SET personal_cap_cents = ? WHERE id = ?",
                [(m["personal_cap_cents"], m["id"]) for m in config["members"]],
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.close()
    print("reset ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
