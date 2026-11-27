# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_child_budget_rule.py
# Pathname:  tests/test_child_budget_rule.py
# Purpose:   Owner rule 2026-11-27: up to the child's budget the wallet decides; above it a parent steps in
from __future__ import annotations

import sqlite3
import threading

import pytest
from conftest import ORDER, dump

STEP_IN = " A parent can step in: use request_approval."


def test_child_exactly_at_remaining_budget_ok(child, ledger):
    r = dump(child.place_order(price_cents=2000, **ORDER))
    assert r["ok"] is True and r["remaining_personal_cents"] == 0
    assert ledger.orders() == 1


def test_child_one_cent_over_refused_with_step_in(child, ledger):
    r = dump(child.place_order(price_cents=2001, **ORDER))
    assert r["ok"] is False and r["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert r["reason"].endswith(STEP_IN)
    assert ledger.state() == (0, 0, 0)


def test_teen_refusal_has_no_step_in(teen):
    r = dump(teen.place_order(price_cents=5001, **ORDER))
    assert r["error_code"] == "PERSONAL_CAP_EXCEEDED" and STEP_IN not in r["reason"]


@pytest.mark.parametrize(
    ("who", "case", "expected"),
    [
        ("child", "fits", False),
        ("child", "over_personal", True),
        ("child", "over_family", False),
        ("child", "no_price", False),
        ("teen", "fits", False),
        ("teen", "over_personal", False),
        ("teen", "over_family", False),
        ("teen", "no_price", False),
        ("parent", "fits", False),
        ("parent", "over_personal", False),
        ("parent", "over_family", False),
        ("parent", "no_price", False),
    ],
)
def test_needs_approval_truth_table(make_service, ledger, who, case, expected):
    ledger.seed_order("parent", 39000)  # family remaining 1000; raised in the over_personal case
    svc = make_service(who)
    if case == "no_price":
        price = None
    elif case == "fits":
        price = 500
    elif case == "over_personal":
        # child cap 2000, teen cap 5000, parent has none; family left 1000 -> raise the family cap
        dump(make_service("parent").set_budget(target="family", cap_cents=100000))
        price = 6000
    else:
        price = 1001
    r = dump(svc.check_budget(price_cents=price))
    assert r["ok"] is True and r["needs_approval"] is expected
    if case == "fits":
        assert r["fits"] is True
    if case == "over_family" or (case == "over_personal" and who != "parent"):
        assert r["fits"] is False


def test_approve_over_budget_request_floors_remaining_and_blocks_next(child, parent, ledger):
    req = dump(child.request_approval(price_cents=3000, **ORDER))
    r = dump(parent.approve_request(request_id=req["request_id"]))
    assert r["ok"] is True
    assert r["remaining_personal_cents"] == 0
    assert r["remaining_family_cents"] == 37000
    b = dump(child.check_budget())
    assert b["remaining_personal_cents"] == 0 and b["personal_spent_cents"] == 3000
    nxt = dump(child.place_order(price_cents=1, **ORDER))
    assert nxt["ok"] is False and nxt["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert nxt["remaining_personal_cents"] == 0
    assert dump(child.check_budget(price_cents=1))["fits"] is False


def test_approval_breaking_family_cap_refused_request_open(child, parent, ledger):
    req = dump(child.request_approval(price_cents=3000, **ORDER))
    ledger.seed_order("parent", 38500)
    r = dump(parent.approve_request(request_id=req["request_id"]))
    assert r["ok"] is False and r["error_code"] == "FAMILY_CAP_EXCEEDED"
    assert ledger.request_status(req["request_id"]) == "open"


def _approve(make_service, rid: int, barrier: threading.Barrier, results: list[dict]) -> None:
    svc = make_service("parent")
    barrier.wait()
    results.append(dump(svc.approve_request(request_id=rid)))


def test_concurrent_approvals_exceeding_family_cap_one_wins(make_service, child, ledger):
    for rnd in range(20):
        conn = sqlite3.connect(ledger.db_path)
        conn.execute("DELETE FROM orders")
        conn.execute("DELETE FROM approval_requests")
        conn.commit()
        conn.close()
        ledger.seed_order("parent", 35000)  # family left 5000; two requests of 3000
        ids = [dump(child.request_approval(price_cents=3000, **ORDER))["request_id"] for _ in range(2)]
        results: list[dict] = []
        barrier = threading.Barrier(2)

        ts = [threading.Thread(target=_approve, args=(make_service, i, barrier, results)) for i in ids]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
        assert sum(1 for r in results if r["ok"]) == 1, (rnd, results)
        assert [r["error_code"] for r in results if not r["ok"]] == ["FAMILY_CAP_EXCEEDED"]
