# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_reject_request.py
# Pathname:  tests/test_reject_request.py
# Purpose:   reject_request: parent-only rejection of a child's request, races, old-db migration, tools
from __future__ import annotations

import sqlite3
import threading

import pytest
from conftest import ORDER, dump

from family_shopper.wallet.db import connect, init_db


def _request(child, cents=1500) -> int:
    return dump(child.request_approval(price_cents=cents, **ORDER))["request_id"]


def test_parent_rejects(parent, child, ledger, raw):
    rid = _request(child)
    r = dump(parent.reject_request(rid))
    assert r == {
        "ok": True, "request_id": rid, "status": "rejected", "member_id": "child",
        "product_name": ORDER["product_name"], "price_cents": 1500, "rejected_by": "parent",
    }  # fmt: skip
    assert ledger.request_status(rid) == "rejected"
    row = raw.execute("SELECT decided_by, decided_at FROM approval_requests WHERE id=?", (rid,)).fetchone()
    assert row["decided_by"] == "parent" and row["decided_at"]
    assert ledger.state() == (0, 1, 0)


@pytest.mark.parametrize("who", ["teen", "child"])
def test_non_parent_cannot_reject(make_service, child, ledger, who):
    rid = _request(child)
    r = dump(make_service(who).reject_request(rid))
    assert r["ok"] is False and r["error_code"] == "NOT_A_PARENT"
    assert ledger.request_status(rid) == "open" and ledger.state() == (0, 1, 0)


def test_reject_twice(parent, child, ledger):
    rid = _request(child)
    assert dump(parent.reject_request(rid))["ok"] is True
    r = dump(parent.reject_request(rid))
    assert r["error_code"] == "REQUEST_NOT_OPEN" and "rejected" in r["reason"]
    assert ledger.request_status(rid) == "rejected"


def test_approve_after_reject(parent, child, ledger):
    rid = _request(child)
    parent.reject_request(rid)
    r = dump(parent.approve_request(rid))
    assert r["error_code"] == "REQUEST_NOT_OPEN"
    assert ledger.state() == (0, 1, 0) and ledger.request_status(rid) == "rejected"


def test_reject_after_approve(parent, child, ledger):
    rid = _request(child)
    assert dump(parent.approve_request(rid))["ok"] is True
    r = dump(parent.reject_request(rid))
    assert r["error_code"] == "REQUEST_NOT_OPEN"
    assert ledger.state() == (1, 1, 1500) and ledger.request_status(rid) == "approved"


def test_unknown_id(parent, ledger):
    assert dump(parent.reject_request(999))["error_code"] == "REQUEST_NOT_FOUND"
    assert ledger.state() == (0, 0, 0)


@pytest.mark.parametrize("bad", ["1", True, None, 1.0])
def test_bad_input(parent, child, ledger, bad):
    _request(child)
    assert dump(parent.reject_request(bad))["error_code"] == "INVALID_INPUT"
    assert ledger.state() == (0, 1, 0)


def test_input_checked_before_role(child):
    assert dump(child.reject_request("x"))["error_code"] == "INVALID_INPUT"


def test_concurrent_approve_and_reject(make_service, child, ledger):
    for _ in range(20):
        rid = _request(child, 10)
        before = ledger.state()
        out: dict[str, dict] = {}
        barrier = threading.Barrier(2)

        def run(name, fn, rid=rid, out=out, barrier=barrier):
            barrier.wait()
            out[name] = dump(fn(rid))

        ts = [
            threading.Thread(target=run, args=("approve", make_service("parent").approve_request)),
            threading.Thread(target=run, args=("reject", make_service("parent").reject_request)),
        ]
        [t.start() for t in ts]
        [t.join() for t in ts]
        oks = [k for k, v in out.items() if v["ok"]]
        assert len(oks) == 1
        loser = next(v for v in out.values() if not v["ok"])
        assert loser["error_code"] == "REQUEST_NOT_OPEN"
        if oks == ["approve"]:
            assert ledger.request_status(rid) == "approved"
            assert ledger.state() == (before[0] + 1, before[1], before[2] + 10)
        else:
            assert ledger.request_status(rid) == "rejected"
            assert ledger.state() == before


def test_list_requests_rejected(parent, child, make_service):
    mine = _request(child)
    other = dump(make_service("child").request_approval(price_cents=500, **ORDER))["request_id"]
    parent.reject_request(mine)
    rows = dump(parent.list_requests("rejected"))["requests"]
    assert [r["request_id"] for r in rows] == [mine] and rows[0]["status"] == "rejected"
    assert [r["request_id"] for r in dump(parent.list_requests())["requests"]] == [other]
    assert [r["request_id"] for r in dump(child.list_requests("rejected"))["requests"]] == [mine]
    assert dump(make_service("teen").list_requests("rejected"))["requests"] == []
    assert dump(parent.list_requests("bogus"))["error_code"] == "INVALID_INPUT"


def test_old_database_is_migrated(tmp_path, config):
    path = tmp_path / "old.sqlite"
    conn = connect(path)
    init_db(conn, config)
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.executescript(
        """
        DROP TABLE approval_requests;
        CREATE TABLE approval_requests (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          member_id TEXT NOT NULL REFERENCES members(id),
          product_name TEXT NOT NULL, shop TEXT NOT NULL, deep_link TEXT NOT NULL,
          price_cents INTEGER NOT NULL CHECK (typeof(price_cents) = 'integer' AND price_cents > 0),
          status TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open','approved')),
          created_at TEXT NOT NULL, decided_at TEXT, decided_by TEXT REFERENCES members(id));
        INSERT INTO approval_requests (member_id, product_name, shop, deep_link, price_cents, created_at)
          VALUES ('child','Buch','s','https://s.test',700,'2026-11-01T00:00:00+00:00');
        """
    )
    conn.close()
    conn = connect(path)
    init_db(conn, config)
    init_db(conn, config)  # idempotent
    row = conn.execute("SELECT id, status, price_cents FROM approval_requests").fetchone()
    assert tuple(row) == (1, "open", 700)
    conn.execute("UPDATE approval_requests SET status='rejected' WHERE id=1")
    assert conn.execute("PRAGMA foreign_key_check").fetchall() == []
    conn.close()
    assert sqlite3.connect(path).execute("SELECT COUNT(*) FROM approval_requests").fetchone()[0] == 1


def test_mcp_lists_eight_tools():
    import asyncio

    from family_shopper.wallet import server

    tools = asyncio.run(server.mcp.list_tools())
    assert len(tools) == 8 and "reject_request" in {t.name for t in tools}
