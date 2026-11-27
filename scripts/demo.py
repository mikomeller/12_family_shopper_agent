#!/usr/bin/env python3
# Author:    mikomeller
# Version:   0.1.2
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

    book_cents = get_product_offers_impl("hobbit-pb")["offers"][0]["total_cents"]

    def scene2() -> None:
        say("Signed in: teen. Prompt: 'Order the SoundMax X1 headphones.'")
        offer = get_product_offers_impl("headphones-x1")["offers"][0]
        say(f"    cheapest offer: {offer['shop']} {fmt_eur(offer['total_cents'])}")
        before = count_orders()
        r = show("place_order", teen.place_order("SoundMax X1", offer["shop"], offer["deep_link"], offer["total_cents"]))
        expect(r["error_code"] == "PERSONAL_CAP_EXCEEDED", "wallet refuses: PERSONAL_CAP_EXCEEDED")
        expect(r["remaining_personal_cents"] is not None, "refusal states the amount left")
        expect(r["reason"].endswith("A parent can step in: use request_approval."), "refusal says a parent can step in")
        say("    Trick: 'split it in two orders'")
        half = offer["total_cents"] // 2
        for i in (1, 2):
            h = show(f"half {i} ({fmt_eur(half)})", teen.place_order(f"SoundMax X1 part {i}", offer["shop"], offer["deep_link"], half))
            expect(h["ok"] is False and h["error_code"] == "PERSONAL_CAP_EXCEEDED", f"half {i} still refused")
        expect(count_orders() == before, "no order was added; spend never exceeds the cap")
        say("Signed in: teen. Prompt: 'Ask a parent for the BrewPro coffee machine.'")
        cm = get_product_offers_impl("coffee-genuine")["offers"][0]
        say(f"    cheapest offer: {cm['shop']} {fmt_eur(cm['total_cents'])}")
        c = show("check_budget", teen.check_budget(cm["total_cents"]))
        expect(c["fits"] is False and c["needs_approval"] is True, "does not fit the teen's budget; a parent can step in")
        r = show("place_order", teen.place_order("BrewPro", cm["shop"], cm["deep_link"], cm["total_cents"]))
        expect(r["error_code"] == "PERSONAL_CAP_EXCEEDED", "order refused: PERSONAL_CAP_EXCEEDED")
        expect(count_orders() == before, "no order, no spend")
        q = show("request_approval", teen.request_approval("BrewPro", cm["shop"], cm["deep_link"], cm["total_cents"]))
        expect(q["ok"] is True and q["status"] == "open", "open request created")
        own = show("approve_request (teen, own request)", teen.approve_request(q["request_id"]))
        expect(own["ok"] is False, "teen cannot approve his own request")
        a = show("approve_request (parent)", parent.approve_request(q["request_id"]))
        expect(a["ok"] is True and a["approved_by"] == "parent", "approved by parent")
        expect(count_orders() == before + 1, "order recorded after the approval")
        expect(a["remaining_personal_cents"] == 0, "teen's remaining budget is 0 (floored)")
        expect(a["remaining_family_cents"] == 40000 - book_cents - cm["total_cents"], "counts against the family cap")

    def scene3() -> None:
        say("Signed in: child. Prompt: 'Order Der Hobbit.' (within the child's budget)")
        book = get_product_offers_impl("hobbit-pb")["offers"][0]
        n0 = count_orders()
        b = show("check_budget", child.check_budget(book["total_cents"]))
        expect(b["fits"] is True and b["needs_approval"] is False, "book fits the child's budget; no approval needed")
        r = show("place_order", child.place_order("Der Hobbit", book["shop"], book["deep_link"], book["total_cents"]))
        expect(r["ok"] is True and count_orders() == n0 + 1, "ordered directly; no parent involved")
        left = 2000 - book["total_cents"]
        expect(r["remaining_personal_cents"] == left, "child's budget reduced")
        say("Signed in: child. Prompt: 'Order the Wuerfelwald board game.' (above the remaining budget)")
        game = min(get_product_offers_impl("boardgame-dice")["offers"], key=lambda o: o["total_cents"])
        say(f"    cheapest offer: {game['shop']} {fmt_eur(game['total_cents'])}")
        expect(game["total_cents"] > left, "the game costs more than the child has left")
        c = show("check_budget", child.check_budget(game["total_cents"]))
        expect(c["fits"] is False and c["needs_approval"] is True, "does not fit; a parent can step in")
        n1 = count_orders()
        r = show("place_order", child.place_order("Wuerfelwald", game["shop"], game["deep_link"], game["total_cents"]))
        expect(r["error_code"] == "PERSONAL_CAP_EXCEEDED", "wallet refuses: PERSONAL_CAP_EXCEEDED")
        expect(r["reason"].endswith("A parent can step in: use request_approval."), "refusal says a parent can step in")
        expect(count_orders() == n1, "no order, no spend")
        q = show("request_approval", child.request_approval("Wuerfelwald", game["shop"], game["deep_link"], game["total_cents"]))
        expect(q["ok"] is True and q["status"] == "open", "open request created")
        expect(count_orders() == n1, "still no spend")
        q2 = show("request_approval (small extra)", child.request_approval("Sticker set", "Shop A", "https://shop.test/sticker", 500))
        expect(q2["ok"] is True, "second small request created")
        say("Signed in: parent. Prompt: 'Show open requests, approve the board game, reject the sticker set.'")
        lr = parent.list_requests().model_dump()["requests"]
        say(f"    open requests: {[(x['request_id'], x['member_id'], x['product_name'], fmt_eur(x['price_cents'])) for x in lr]}")
        expect(len(lr) == 2, "parent sees exactly two open requests")
        a = show("approve_request", parent.approve_request(q["request_id"]))
        expect(a["ok"] is True and a["approved_by"] == "parent", "approved by parent")
        expect(a["remaining_personal_cents"] == 0, "child's remaining budget is 0 (floored)")
        coffee = get_product_offers_impl("coffee-genuine")["offers"][0]["total_cents"]
        fam = 40000 - 2 * book["total_cents"] - coffee - game["total_cents"]  # scenes 1 and 2 spent for the teen
        expect(a["remaining_family_cents"] == fam, "counts against the family cap")
        rj = show("reject_request", parent.reject_request(q2["request_id"]))
        expect(rj["ok"] is True, "second request rejected")
        expect(count_orders() == n1 + 1, "the rejected request never became an order")

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
