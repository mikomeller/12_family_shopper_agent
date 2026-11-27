# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_l1_caps.py
# Pathname:  tests/test_l1_caps.py
# Purpose:   L1-01..L1-13 cap logic of the Family Wallet service (deterministic, no network, no LLM)
from __future__ import annotations

import threading
from datetime import UTC, datetime

import pytest
from conftest import ORDER, dump


def order(svc, cents):
    return dump(svc.place_order(price_cents=cents, **ORDER))


def test_l1_01_teen_orders_within_cap(teen, ledger):
    r = order(teen, 2500)
    assert r["ok"] is True
    assert r["remaining_personal_cents"] == 2500
    assert r["remaining_family_cents"] == 37500
    assert ledger.orders() == 1 and ledger.spent() == 2500


def test_l1_02_personal_cap_refuses_teen(teen, ledger):
    assert order(teen, 2500)["ok"] is True
    before = ledger.state()
    r = order(teen, 3000)
    assert r["ok"] is False
    assert r["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert r["remaining_personal_cents"] == 2500
    assert ledger.state() == before


def test_l1_03_family_cap_refuses_parent(parent, ledger):
    ledger.seed_order("parent", 39000)
    before = ledger.state()
    r = order(parent, 2000)
    assert r["ok"] is False
    assert r["error_code"] == "FAMILY_CAP_EXCEEDED"
    assert r["remaining_family_cents"] == 1000
    assert ledger.state() == before


def test_l1_04_teen_fills_family_cap_exactly(teen, ledger):
    ledger.seed_order("parent", 39000)
    r = order(teen, 1000)
    assert r["ok"] is True
    assert r["remaining_family_cents"] == 0
    assert ledger.spent() == 40000


def test_l1_05_child_request_creates_no_order_no_spend(child, ledger):
    r = dump(child.request_approval(price_cents=1000, **ORDER))
    assert r["ok"] is True
    assert r["status"] == "open"
    assert r["member_id"] == "child"
    assert ledger.requests() == 1
    assert ledger.orders() == 0 and ledger.spent() == 0


def test_l1_06_parent_approves_child_request(child, parent, ledger):
    req = dump(child.request_approval(price_cents=1000, **ORDER))
    r = dump(parent.approve_request(request_id=req["request_id"]))
    assert r["ok"] is True
    assert r["member_id"] == "child"
    assert r["approved_by"] == "parent"
    assert r["remaining_personal_cents"] == 1000  # counts against the child's 2000 cap (A1)
    assert r["remaining_family_cents"] == 39000
    assert ledger.orders() == 1 and ledger.spent() == 1000
    assert ledger.request_status(req["request_id"]) == "approved"
    # the approved order counts against the child's personal cap
    assert dump(child.check_budget(price_cents=1500))["fits"] is False


def test_l1_07_approve_that_no_longer_fits_stays_open(child, parent, ledger):
    req = dump(child.request_approval(price_cents=1500, **ORDER))
    ledger.seed_order("child", 1000)  # child spent elsewhere meanwhile; 1000 + 1500 > 2000
    before = ledger.state()
    r = dump(parent.approve_request(request_id=req["request_id"]))
    assert r["ok"] is False
    assert r["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert r["remaining_personal_cents"] == 1000
    assert ledger.request_status(req["request_id"]) == "open"
    assert ledger.state() == before


def test_l1_07b_approve_that_breaks_family_cap_stays_open(child, parent, ledger):
    req = dump(child.request_approval(price_cents=1500, **ORDER))
    ledger.seed_order("parent", 39000)
    before = ledger.state()
    r = dump(parent.approve_request(request_id=req["request_id"]))
    assert r["ok"] is False
    assert r["error_code"] == "FAMILY_CAP_EXCEEDED"
    assert r["remaining_family_cents"] == 1000
    assert ledger.request_status(req["request_id"]) == "open"
    assert ledger.state() == before


def test_l1_08_teen_cannot_approve(child, teen, ledger):
    req = dump(child.request_approval(price_cents=1000, **ORDER))
    before = ledger.state()
    r = dump(teen.approve_request(request_id=req["request_id"]))
    assert r["ok"] is False
    assert r["error_code"] == "NOT_A_PARENT"
    assert r["reason"] == "Only a parent can approve requests."
    assert ledger.request_status(req["request_id"]) == "open"
    assert ledger.state() == before


def test_l1_09_new_month_starts_at_zero(teen, clock, ledger):
    # 2026-11-30 22:30 UTC is 23:30 in Berlin: still November
    clock.set(datetime(2026, 11, 30, 22, 30, tzinfo=UTC))
    assert order(teen, 5000)["ok"] is True
    r = dump(teen.check_budget())
    assert r["month"] == "2026-11" and r["remaining_personal_cents"] == 0
    assert order(teen, 100)["error_code"] == "PERSONAL_CAP_EXCEEDED"
    # 2026-11-30 23:30 UTC is 00:30 on 1 December in Berlin: new month
    clock.set(datetime(2026, 11, 30, 23, 30, tzinfo=UTC))
    r = dump(teen.check_budget())
    assert r["month"] == "2026-12"
    assert r["personal_spent_cents"] == 0 and r["family_spent_cents"] == 0
    assert r["remaining_personal_cents"] == 5000
    r = order(teen, 5000)
    assert r["ok"] is True and r["month"] == "2026-12"
    assert ledger.orders() == 2


@pytest.mark.parametrize("round_no", range(25))
def test_l1_10_concurrent_orders_exactly_one_succeeds(make_service, ledger, round_no):
    results: list[dict] = []
    barrier = threading.Barrier(2)

    def worker():
        svc = make_service("teen")  # own service, own connection per call
        barrier.wait()
        results.append(order(svc, 3000))

    threads = [threading.Thread(target=worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=30)
    assert len(results) == 2
    assert sorted(r["ok"] for r in results) == [False, True]
    refused = next(r for r in results if not r["ok"])
    assert refused["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert ledger.orders() == 1 and ledger.spent() == 3000


@pytest.mark.parametrize("bad", [0, -1, -5000, 10.5, 25.0, "2500", "abc", True, False, None])
def test_l1_11_invalid_amount_refused(teen, ledger, bad):
    r = dump(teen.place_order(price_cents=bad, **ORDER))
    assert r["ok"] is False
    assert r["error_code"] == "INVALID_AMOUNT"
    assert r["reason"] == "The amount must be a whole number of cents greater than zero."
    assert ledger.state() == (0, 0, 0)


def test_l1_12_order_exactly_at_cap(teen, ledger):
    r = order(teen, 5000)
    assert r["ok"] is True
    assert r["remaining_personal_cents"] == 0
    assert ledger.spent() == 5000


def test_l1_13_one_cent_over_cap_refused(teen, ledger):
    r = order(teen, 5001)
    assert r["ok"] is False
    assert r["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert r["remaining_personal_cents"] == 5000
    assert ledger.state() == (0, 0, 0)
    assert order(teen, 5000)["ok"] is True  # and 5000 still fits
