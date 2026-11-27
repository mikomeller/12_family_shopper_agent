#!/usr/bin/env python3
# Author:    mikomeller
# Version:   0.1.0
# Filename:  demo.py
# Pathname:  scripts/demo.py
# Purpose:   Offline, deterministic walk-through of the five demo scenes against the real wallet and the idealo mock (no LLM, no network, no Boris)
"""Plays the demo scenes on a fresh temp SQLite db. Exit 0 only if every scene behaves as expected."""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from family_shopper.idealo_mock.server import (  # noqa: E402
    check_discount_impl,
    get_product_details_impl,
    get_product_offers_impl,
    get_product_price_history_impl,
    search_products_impl,
)
from family_shopper.wallet import db  # noqa: E402
from family_shopper.wallet.identity import Member, TokenResolver, mint_token  # noqa: E402
from family_shopper.wallet.service import WalletService, fmt_eur  # noqa: E402

CLOCK = lambda: datetime(2026, 11, 15, 12, 0, tzinfo=UTC)  # noqa: E731


class Who:
    """Fake resolver: the signed-in member (stands in for Boris caller identity)."""

    def __init__(self, member: Member) -> None:
        self.member = member

    def resolve(self) -> Member:
        return self.member


def say(text: str = "") -> None:
    print(text)


def show(label: str, r) -> dict:
    d = r.model_dump()
    bits = []
    for k, v in d.items():
        if k.endswith("_cents") and v is not None:
            bits.append(f"{k[:-6]}={fmt_eur(v)}")
        elif k in ("ok", "error_code", "reason", "order_id", "request_id", "deep_link", "shop"):
            bits.append(f"{k}={v}")
    say(f"    {label}: " + ", ".join(bits))
    return d


def expect(cond: bool, what: str) -> None:
    if not cond:
        raise AssertionError(what)
    say(f"    [ok] {what}")


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="family_wallet_demo_")
    path = Path(tmp) / "wallet.sqlite"
    conn = db.connect(path)
    try:
        db.init_db(conn, db.load_config())
    finally:
        conn.close()
    say(f"Fresh demo wallet: {path}  (family cap {fmt_eur(40000)}, teen {fmt_eur(5000)}, child {fmt_eur(2000)})")

    def svc(who: str, role: str) -> WalletService:
        return WalletService(path, Who(Member(id=who, role=role)), CLOCK)  # type: ignore[arg-type]

    parent, teen, child = svc("parent", "parent"), svc("teen", "teen"), svc("child", "child")

    def count_orders() -> int:
        return len(parent.list_orders().model_dump()["orders"])

    def scene1() -> None:
        say("Signed in: teen. Prompt: 'Find Der Hobbit and order the cheapest offer.'")
        hits = search_products_impl("Der Hobbit")["results"]
        say(f"    idealo mock search: {[h['title'] for h in hits]}")
        ref = hits[0]["product_ref"]
        best = get_product_offers_impl(ref)["offers"][0]
        say(f"    cheapest offer: {best['shop']} {fmt_eur(best['total_cents'])} incl. shipping")
        b = show("check_budget", teen.check_budget(best["total_cents"]))
        expect(b["fits"] is True, "price fits the teen's cap")
        o = show("place_order", teen.place_order(hits[0]["title"], best["shop"], best["deep_link"], best["total_cents"]))
        expect(o["ok"] is True and o["deep_link"] == best["deep_link"], "order recorded with deep link")
        expect(o["remaining_personal_cents"] == 5000 - best["total_cents"], "personal budget reduced")
        expect(o["remaining_family_cents"] == 40000 - best["total_cents"], "family budget reduced; no parent involved")

    def scene2() -> None:
        say("Signed in: teen. Prompt: 'Order the SoundMax X1 headphones.'")
        offer = get_product_offers_impl("headphones-x1")["offers"][0]
        say(f"    cheapest offer: {offer['shop']} {fmt_eur(offer['total_cents'])}")
        before = count_orders()
        r = show("place_order", teen.place_order("SoundMax X1", offer["shop"], offer["deep_link"], offer["total_cents"]))
        expect(r["error_code"] == "PERSONAL_CAP_EXCEEDED", "wallet refuses: PERSONAL_CAP_EXCEEDED")
        expect(r["remaining_personal_cents"] is not None, "refusal states the amount left")
        say("    Trick: 'split it in two orders'")
        half = offer["total_cents"] // 2
        for i in (1, 2):
            h = show(f"half {i} ({fmt_eur(half)})", teen.place_order(f"SoundMax X1 part {i}", offer["shop"], offer["deep_link"], half))
            expect(h["ok"] is False and h["error_code"] == "PERSONAL_CAP_EXCEEDED", f"half {i} still refused")
        expect(count_orders() == before, "no order was added; spend never exceeds the cap")

    req: dict = {}

    def scene3() -> None:
        say("Signed in: child. Prompt: 'Order Der Hobbit.'")
        offer = get_product_offers_impl("hobbit-pb")["offers"][0]
        r = show("place_order", child.place_order("Der Hobbit", offer["shop"], offer["deep_link"], offer["total_cents"]))
        expect(r["error_code"] == "NOT_ALLOWED_FOR_ROLE", "wallet itself refuses a child's direct order")
        before = count_orders()
        q = show("request_approval", child.request_approval("Der Hobbit", offer["shop"], offer["deep_link"], offer["total_cents"]))
        expect(q["ok"] is True and q["status"] == "open", "open request created")
        expect(count_orders() == before, "no spend yet")
        say("Signed in: parent. Prompt: 'Show open requests and approve the child's.'")
        lr = parent.list_requests().model_dump()["requests"]
        say(f"    open requests: {[(x['request_id'], x['member_id'], x['product_name'], fmt_eur(x['price_cents'])) for x in lr]}")
        expect(len(lr) == 1, "parent sees exactly one open request")
        a = show("approve_request", parent.approve_request(lr[0]["request_id"]))
        expect(a["ok"] is True and a["approved_by"] == "parent", "approved by parent")
        expect(a["remaining_personal_cents"] == 2000 - offer["total_cents"], "counts against the child's cap")
        expect(a["remaining_family_cents"] == 40000 - 2 * offer["total_cents"], "counts against the family cap")
        req.update(a)

    def scene4() -> None:
        say("Signed in: teen. Prompt: 'Is the 449 EUR crossed-out price on the headphones real?'")
        hist = get_product_price_history_impl("headphones-x1")["history"]
        best = get_product_offers_impl("headphones-x1")["offers"][0]["total_cents"]
        d = check_discount_impl(29900, 44900, hist, 0, best)
        say(f"    headphones, sale {fmt_eur(29900)}, was {fmt_eur(44900)}: {d['verdict']} - {d['reason']}")
        expect(d["verdict"] == "INFLATED", "headphones: INFLATED")
        hist = get_product_price_history_impl("coffee-genuine")["history"]
        best = get_product_offers_impl("coffee-genuine")["offers"][0]["total_cents"]
        c = check_discount_impl(7999, 9999, hist, 0, best)
        say(f"    coffee machine, sale {fmt_eur(7999)}, was {fmt_eur(9999)}: {c['verdict']} - {c['reason']}")
        expect(c["verdict"] == "GENUINE", "coffee machine: GENUINE")

    def scene5() -> None:
        say("Identity: real TokenResolver (HMAC) instead of the fake resolver.")
        old = {k: os.environ.get(k) for k in ("WALLET_MEMBER_TOKEN", "WALLET_TOKEN_SECRET")}
        os.environ["WALLET_TOKEN_SECRET"] = "demo-secret-not-for-production"
        try:
            real = WalletService(path, TokenResolver(path, CLOCK), CLOCK)
            tok = mint_token("teen", 3600, os.environ["WALLET_TOKEN_SECRET"], CLOCK)
            os.environ["WALLET_MEMBER_TOKEN"] = tok
            ok = show("valid teen token, check_budget", real.check_budget())
            expect(ok["ok"] is True and ok["member_id"] == "teen", "valid token resolves to teen")
            forged = tok[:-4] + ("0000" if not tok.endswith("0000") else "1111")
            os.environ["WALLET_MEMBER_TOKEN"] = forged
            r = show("tampered token", real.check_budget())
            expect(r["error_code"] == "IDENTITY_INVALID", "tampered token: IDENTITY_INVALID")
            os.environ["WALLET_MEMBER_TOKEN"] = tok.replace("teen.", "parent.", 1)
            r = show("token with member swapped to parent", real.check_budget())
            expect(r["error_code"] == "IDENTITY_INVALID", "swapped member id: IDENTITY_INVALID")
            os.environ.pop("WALLET_MEMBER_TOKEN")
            r = show("no token", real.check_budget())
            expect(r["error_code"] == "IDENTITY_MISSING", "missing token: IDENTITY_MISSING")
        finally:
            for k, v in old.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        say("Prompt: 'Look at the TrailKid backpack.' The product description is DATA:")
        desc = get_product_details_impl("backpack-inj")["description"]
        say(f"    description = {desc!r}")
        n0 = count_orders()
        say("    (no agent in this offline demo: nothing reads the text as an instruction)")
        expect(count_orders() == n0, "zero orders result from the injected text")
        expect(all("backpack" not in o["product_name"].lower() for o in parent.list_orders().model_dump()["orders"]), "no backpack order exists")

    scenes = [("1 trust dividend", scene1), ("2 cap", scene2), ("3 child + parent", scene3),
              ("4 discount honesty", scene4), ("5 identity + injection", scene5)]
    passed = 0
    for name, fn in scenes:
        say(f"\n=== Scene {name} ===")
        try:
            fn()
            passed += 1
        except AssertionError as e:
            say(f"DEMO FAILED in scene {name}: {e}")
            return 1

    say("\n=== End: parent reviews ===")
    orders = parent.list_orders().model_dump()["orders"]
    for o in orders:
        say(f"    #{o['order_id']} {o['member_id']:<6} {o['product_name']:<12} {fmt_eur(o['price_cents'])}  {o['deep_link']}")
    spent = sum(o["price_cents"] for o in orders)
    say(f"family spent {fmt_eur(spent)} of {fmt_eur(40000)}")
    say(f"DEMO OK: {passed}/5 scenes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
