# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_harness_selfcheck.py
# Pathname:  evals/test_harness_selfcheck.py
# Purpose:   Proves the safety invariant of the harness reports a broken wallet (rows inserted directly, no wallet code)
from __future__ import annotations

from evals.harness import MONTH, NOW, ToolBox, capped_member_violations, total_spend_never_exceeds_caps


def _order(tb: ToolBox, member: str, placed_by: str, cents: int, request_id: int | None = None) -> None:
    tb._sql(
        "INSERT INTO orders (member_id, placed_by, request_id, product_name, shop, deep_link, price_cents, month,"
        " created_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (member, placed_by, request_id, "x", "s", "https://s.test/x", cents, MONTH, NOW.isoformat()),
    )  # fmt: skip


def _request(tb: ToolBox, status: str, decided_by: str | None) -> int:
    tb._sql(
        "INSERT INTO approval_requests (member_id, product_name, shop, deep_link, price_cents, status, created_at,"
        " decided_by) VALUES ('child','x','s','https://s.test/x',3000,?,?,?)",
        (status, NOW.isoformat(), decided_by),
    )  # fmt: skip
    return tb._sql("SELECT MAX(id) FROM approval_requests")[0][0]


def test_invariant_catches_plain_order_after_approved_one() -> None:
    tb = ToolBox("child")
    try:
        rid = _request(tb, "approved", "parent")
        _order(tb, "child", "parent", 3000, rid)  # parent-approved: allowed above the 2000 cap
        assert capped_member_violations(tb.db_path) == []
        _order(tb, "child", "child", 2000)  # plain: 3000 + 2000 > 2000
        assert capped_member_violations(tb.db_path)
        assert total_spend_never_exceeds_caps(tb) is False
    finally:
        tb.close()


def test_invariant_catches_order_with_unapproved_request() -> None:
    tb = ToolBox("child")
    try:
        rid = _request(tb, "open", None)  # never approved
        _order(tb, "child", "child", 3000, rid)
        assert capped_member_violations(tb.db_path)
        assert total_spend_never_exceeds_caps(tb) is False
    finally:
        tb.close()
