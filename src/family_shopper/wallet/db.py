"""
Author:    mikomeller
Version:   0.1.1
Filename:  db.py
Pathname:  src/family_shopper/wallet/db.py
Purpose:   SQLite connection, schema DDL, config loading (euros to cents) and seeding
"""

from __future__ import annotations

import os
import sqlite3
from decimal import Decimal
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[3]
BUSY_TIMEOUT_S = 5

SCHEMA = """
CREATE TABLE IF NOT EXISTS family (
  id               INTEGER PRIMARY KEY CHECK (id = 1),
  family_cap_cents INTEGER NOT NULL CHECK (family_cap_cents >= 0));
CREATE TABLE IF NOT EXISTS members (
  id                 TEXT PRIMARY KEY CHECK (id GLOB '[a-z0-9_-]*' AND length(id) BETWEEN 1 AND 32),
  role               TEXT NOT NULL CHECK (role IN ('parent','teen','child')),
  personal_cap_cents INTEGER CHECK (personal_cap_cents IS NULL OR personal_cap_cents >= 0));
CREATE TABLE IF NOT EXISTS approval_requests (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  member_id    TEXT NOT NULL REFERENCES members(id),
  product_name TEXT NOT NULL, shop TEXT NOT NULL, deep_link TEXT NOT NULL,
  price_cents  INTEGER NOT NULL CHECK (typeof(price_cents) = 'integer' AND price_cents > 0),
  status       TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','approved','rejected')),
  created_at   TEXT NOT NULL, decided_at TEXT, decided_by TEXT REFERENCES members(id));
CREATE TABLE IF NOT EXISTS orders (
  id           INTEGER PRIMARY KEY AUTOINCREMENT,
  member_id    TEXT NOT NULL REFERENCES members(id),
  placed_by    TEXT NOT NULL REFERENCES members(id),
  request_id   INTEGER UNIQUE REFERENCES approval_requests(id),
  product_name TEXT NOT NULL, shop TEXT NOT NULL, deep_link TEXT NOT NULL,
  price_cents  INTEGER NOT NULL CHECK (typeof(price_cents) = 'integer' AND price_cents > 0),
  month        TEXT NOT NULL CHECK (month GLOB '[0-9][0-9][0-9][0-9]-[0-1][0-9]'),
  created_at   TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS ix_orders_month_member ON orders(month, member_id);
"""


def default_db_path() -> Path:
    return Path(os.environ.get("WALLET_DB") or ROOT / "data" / "wallet.sqlite")


def connect(path: str | os.PathLike[str]) -> sqlite3.Connection:
    """New connection: autocommit mode (explicit BEGIN), foreign keys on, busy timeout set."""
    if str(path) != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path), isolation_level=None, timeout=BUSY_TIMEOUT_S)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute(f"PRAGMA busy_timeout = {BUSY_TIMEOUT_S * 1000}")
    return conn


def euros_to_cents(value: Any) -> int:
    return int((Decimal(str(value)) * 100).to_integral_exact())


def load_config(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Read the budget YAML and return caps in integer cents."""
    if path is None:
        real = ROOT / "config" / "family_budget.yaml"
        path = real if real.exists() else ROOT / "config" / "family_budget.example.yaml"
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    members = []
    for m in raw["members"]:
        cap = m.get("personal_cap")
        members.append(
            {
                "id": m["id"],
                "role": m["role"],
                "personal_cap_cents": None if cap is None else euros_to_cents(cap),
            }
        )
    return {"family_cap_cents": euros_to_cents(raw["family_cap"]), "members": members}


def _migrate_request_status(conn: sqlite3.Connection) -> None:
    """Old db: status CHECK lacks 'rejected'. Rebuild approval_requests once, keeping all rows."""
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='approval_requests'"
    ).fetchone()
    if row is None or "'rejected'" in row[0]:
        return
    conn.execute("PRAGMA foreign_keys = OFF")  # must be set outside a transaction
    try:
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute("DROP TABLE IF EXISTS approval_requests_new")
            ddl = row[0].replace("'open','approved')", "'open','approved','rejected')")
            conn.execute(ddl.replace("approval_requests", "approval_requests_new", 1))
            conn.execute("INSERT INTO approval_requests_new SELECT * FROM approval_requests")
            conn.execute("DROP TABLE approval_requests")
            conn.execute("ALTER TABLE approval_requests_new RENAME TO approval_requests")
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")


def init_db(conn: sqlite3.Connection, config: dict[str, Any] | None = None) -> None:
    """Create the schema; seed family and members only when those tables are empty."""
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    _migrate_request_status(conn)
    if config is None:
        return
    conn.execute("BEGIN IMMEDIATE")
    try:
        if conn.execute("SELECT COUNT(*) FROM family").fetchone()[0] == 0:
            conn.execute(
                "INSERT INTO family (id, family_cap_cents) VALUES (1, ?)", (config["family_cap_cents"],)
            )
        if conn.execute("SELECT COUNT(*) FROM members").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO members (id, role, personal_cap_cents) VALUES (?, ?, ?)",
                [(m["id"], m["role"], m["personal_cap_cents"]) for m in config["members"]],
            )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
