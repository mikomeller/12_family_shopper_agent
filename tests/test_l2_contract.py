# Author:    mikomeller
# Version:   0.1.1
# Filename:  test_l2_contract.py
# Pathname:  tests/test_l2_contract.py
# Purpose:   L2-01..L2-09 tool contract and identity of the Family Wallet (deterministic, no network, no LLM)
from __future__ import annotations

import asyncio
import json

import pytest
from conftest import ORDER, dump

from family_shopper.wallet.identity import TokenResolver, mint_token
from family_shopper.wallet.service import WalletService

SECRET = "test-secret-not-real"
TOOLS = {
    "check_budget", "place_order", "request_approval", "approve_request",
    "set_budget", "list_orders", "list_requests", "reject_request",
}


@pytest.fixture
def token_service(db_path, clock, monkeypatch):
    """WalletService wired to the real TokenResolver; the token comes from the environment."""
    monkeypatch.setenv("WALLET_TOKEN_SECRET", SECRET)
    monkeypatch.delenv("WALLET_MEMBER_TOKEN", raising=False)
    return WalletService(db_path, TokenResolver(db_path, clock), clock)


def token_for(member_id, clock, secret=SECRET, ttl=3600):
    return mint_token(member_id, ttl, secret, clock)


# ---------------------------------------------------------------- L2-01 / L2-02
def test_l2_01_each_tool_valid_input_matches_schema(parent, teen, child, ledger):
    chk = dump(teen.check_budget(price_cents=1000))
    assert chk["ok"] is True
    assert {"member_id", "role", "month", "personal_cap_cents", "personal_spent_cents",
            "remaining_personal_cents", "family_cap_cents", "family_spent_cents",
            "remaining_family_cents", "needs_approval", "fits"} <= chk.keys()
    assert chk["personal_cap_cents"] == 5000 and chk["family_cap_cents"] == 40000
    assert chk["needs_approval"] is False and chk["fits"] is True
    assert dump(teen.check_budget())["fits"] is None
    assert dump(child.check_budget())["needs_approval"] is False  # no price
    assert dump(child.check_budget(price_cents=2500))["needs_approval"] is True
    assert dump(parent.check_budget())["personal_cap_cents"] is None

    po = dump(teen.place_order(price_cents=1000, **ORDER))
    assert po["ok"] is True and isinstance(po["order_id"], int)

    ra = dump(child.request_approval(price_cents=500, **ORDER))
    assert {"request_id", "status", "member_id", "price_cents",
            "remaining_personal_cents", "remaining_family_cents"} <= ra.keys()

    ap = dump(parent.approve_request(request_id=ra["request_id"]))
    assert ap["ok"] is True and ap["request_id"] == ra["request_id"] and ap["approved_by"] == "parent"

    sb = dump(parent.set_budget(target="teen", cap_cents=7000))
    assert sb == {"ok": True, "target": "teen", "cap_cents": 7000}
    assert dump(parent.set_budget(target="family", cap_cents=50000))["cap_cents"] == 50000

    lo = dump(parent.list_orders())
    assert lo["ok"] is True and lo["month"] == "2026-11" and len(lo["orders"]) == 2
    assert {"order_id", "member_id", "placed_by", "product_name", "shop", "deep_link",
            "price_cents", "created_at", "request_id"} <= lo["orders"][0].keys()

    ra2 = dump(child.request_approval(price_cents=300, **ORDER))
    lr = dump(parent.list_requests())
    assert lr["ok"] is True and [x["request_id"] for x in lr["requests"]] == [ra2["request_id"]]
    assert {"request_id", "member_id", "product_name", "shop", "deep_link", "price_cents",
            "status", "created_at"} <= lr["requests"][0].keys()


def test_l2_02_bad_input_gives_structured_error_no_state_change(teen, parent, child, ledger):
    before = ledger.state()
    bad_calls = [
        (teen.place_order, dict(product_name="", shop="s", deep_link="l", price_cents=100), "INVALID_INPUT"),
        (teen.place_order, dict(product_name="p", shop=None, deep_link="l", price_cents=100),
         "INVALID_INPUT"),
        (teen.place_order, dict(product_name=5, shop="s", deep_link="l", price_cents=100), "INVALID_INPUT"),
        (teen.place_order, dict(product_name="x" * 501, shop="s", deep_link="l", price_cents=100),
         "INVALID_INPUT"),
        (teen.place_order, dict(product_name="p", shop="s", deep_link="l", price_cents="100"),
         "INVALID_AMOUNT"),
        (child.request_approval, dict(product_name="p", shop="", deep_link="l", price_cents=100),
         "INVALID_INPUT"),
        (child.request_approval, dict(product_name="p", shop="s", deep_link="l", price_cents=0),
         "INVALID_AMOUNT"),
        (teen.check_budget, dict(price_cents=-1), "INVALID_AMOUNT"),
        (teen.check_budget, dict(price_cents=1.5), "INVALID_AMOUNT"),
        (parent.approve_request, dict(request_id="1"), "INVALID_INPUT"),
        (parent.approve_request, dict(request_id=None), "INVALID_INPUT"),
        (parent.set_budget, dict(target="", cap_cents=100), "INVALID_INPUT"),
        (parent.set_budget, dict(target="teen", cap_cents=-1), "INVALID_AMOUNT"),
        (parent.set_budget, dict(target="teen", cap_cents="100"), "INVALID_AMOUNT"),
        (parent.set_budget, dict(target="teen", cap_cents=True), "INVALID_AMOUNT"),
        (parent.set_budget, dict(target="nobody", cap_cents=100), "MEMBER_NOT_FOUND"),
    ]
    for fn, kwargs, code in bad_calls:
        r = dump(fn(**kwargs))
        assert r["ok"] is False, (fn.__name__, kwargs)
        assert r["error_code"] == code, (fn.__name__, kwargs, r)
        assert isinstance(r["reason"], str) and r["reason"]
    assert ledger.state() == before
    # caps untouched by the refused set_budget calls
    assert dump(teen.check_budget())["personal_cap_cents"] == 5000


# ---------------------------------------------------------------- L2-03 / L2-04
def test_l2_03_missing_identity_refused(token_service, ledger, monkeypatch):
    r = dump(token_service.place_order(price_cents=100, **ORDER))
    assert r["ok"] is False and r["error_code"] == "IDENTITY_MISSING"
    assert r["reason"] == "No caller identity was provided."
    assert r["remaining_personal_cents"] is None and r["remaining_family_cents"] is None
    monkeypatch.setenv("WALLET_MEMBER_TOKEN", "")
    assert dump(token_service.check_budget())["error_code"] == "IDENTITY_MISSING"
    for fn, kw in [(token_service.list_orders, {}), (token_service.list_requests, {}),
                   (token_service.set_budget, dict(target="teen", cap_cents=1)),
                   (token_service.approve_request, dict(request_id=1)),
                   (token_service.request_approval, dict(price_cents=100, **ORDER))]:
        assert dump(fn(**kw))["error_code"] == "IDENTITY_MISSING"
    assert ledger.state() == (0, 0, 0)


def test_l2_03b_valid_token_works(token_service, clock, monkeypatch, ledger):
    monkeypatch.setenv("WALLET_MEMBER_TOKEN", token_for("teen", clock))
    r = dump(token_service.place_order(price_cents=100, **ORDER))
    assert r["ok"] is True and r["member_id"] == "teen"


def _forged(kind, clock):
    good = token_for("teen", clock)
    member, expiry, sig = good.split(".")
    if kind == "tampered_signature":
        return f"{member}.{expiry}.{'0' * len(sig)}"
    if kind == "tampered_member":  # teen's signature replayed for the parent
        return f"parent.{expiry}.{sig}"
    if kind == "tampered_expiry":
        return f"{member}.{int(expiry) + 99999}.{sig}"
    if kind == "expired":
        return mint_token("teen", -60, SECRET, clock)
    if kind == "expired_exact":
        return mint_token("teen", 0, SECRET, clock)
    if kind == "unknown_member":
        return token_for("ghost", clock)
    if kind == "wrong_secret":
        return token_for("teen", clock, secret="another-secret")
    if kind == "garbage":
        return "not-a-token"
    if kind == "too_many_parts":
        return f"{good}.extra"
    raise AssertionError(kind)


@pytest.mark.parametrize("kind", ["tampered_signature", "tampered_member", "tampered_expiry", "expired",
                                  "expired_exact", "unknown_member", "wrong_secret", "garbage",
                                  "too_many_parts"])
def test_l2_04_forged_identity_refused(token_service, clock, monkeypatch, ledger, kind):
    monkeypatch.setenv("WALLET_MEMBER_TOKEN", _forged(kind, clock))
    r = dump(token_service.place_order(price_cents=100, **ORDER))
    assert r["ok"] is False and r["error_code"] == "IDENTITY_INVALID"
    assert r["reason"] == "The caller identity is invalid or expired."
    assert ledger.state() == (0, 0, 0)


def test_l2_04b_secret_unset_fails_closed(token_service, clock, monkeypatch, ledger):
    monkeypatch.setenv("WALLET_MEMBER_TOKEN", token_for("teen", clock))
    monkeypatch.delenv("WALLET_TOKEN_SECRET")
    assert dump(token_service.check_budget())["error_code"] == "IDENTITY_INVALID"
    monkeypatch.setenv("WALLET_TOKEN_SECRET", "")
    assert dump(token_service.check_budget())["error_code"] == "IDENTITY_INVALID"
    assert ledger.state() == (0, 0, 0)


# ---------------------------------------------------------------- L2-05
def _server_tools():
    from family_shopper.wallet import server

    for name in ("mcp", "server", "app"):
        if hasattr(server, name):
            srv = getattr(server, name)
            break
    else:
        raise AssertionError("no MCP server object (mcp/server/app) in wallet.server")
    return asyncio.run(srv.list_tools())


def test_l2_05_no_tool_accepts_a_member_argument():
    tools = _server_tools()
    assert {t.name for t in tools} == TOOLS
    forbidden = ("member", "caller", "user", "who", "identity", "token", "as_")
    for tool in tools:
        props = (tool.input_schema or {}).get("properties", {})
        for prop in props:
            assert not any(f in prop.lower() for f in forbidden), (tool.name, prop)
    # set_budget's `target` is the budget to change, not the caller
    sb = next(t for t in tools if t.name == "set_budget")
    assert set(sb.input_schema["properties"]) == {"target", "cap_cents"}


def test_l2_05b_member_argument_cannot_select_the_caller(teen, ledger):
    with pytest.raises(TypeError):
        teen.place_order(member_id="parent", price_cents=100, **ORDER)
    with pytest.raises(TypeError):
        teen.check_budget(member="parent")
    assert ledger.state() == (0, 0, 0)


def test_l2_05c_token_decides_member_not_arguments(token_service, clock, monkeypatch):
    monkeypatch.setenv("WALLET_MEMBER_TOKEN", token_for("teen", clock))
    r = dump(token_service.check_budget())
    assert r["member_id"] == "teen" and r["role"] == "teen"


# ---------------------------------------------------------------- L2-06 / L2-07
def test_l2_06_child_place_order_refused_by_wallet(child, ledger):
    r = dump(child.place_order(price_cents=2500, **ORDER))  # above the 2000 cap
    assert r["ok"] is False and r["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert r["reason"].endswith(" A parent can step in: use request_approval.")
    assert ledger.state() == (0, 0, 0)


def test_l2_06b_parent_and_teen_cannot_request_approval(parent, teen, ledger):
    for svc in (parent, teen):
        r = dump(svc.request_approval(price_cents=100, **ORDER))
        assert r["ok"] is False and r["error_code"] == "NOT_ALLOWED_FOR_ROLE"
    assert ledger.state() == (0, 0, 0)


@pytest.mark.parametrize("who", ["teen", "child"])
def test_l2_07_non_parent_cannot_set_budget_or_approve(who, make_service, child, ledger):
    svc = make_service(who)
    req = dump(child.request_approval(price_cents=500, **ORDER))
    before = ledger.state()
    r = dump(svc.set_budget(target="teen", cap_cents=999999))
    assert r["ok"] is False and r["error_code"] == "NOT_A_PARENT"
    assert r["reason"] == "Only a parent can set budgets."
    r = dump(svc.set_budget(target="family", cap_cents=999999))
    assert r["error_code"] == "NOT_A_PARENT"
    r = dump(svc.approve_request(request_id=req["request_id"]))
    assert r["ok"] is False and r["error_code"] == "NOT_A_PARENT"
    assert r["reason"] == "Only a parent can approve requests."
    assert ledger.state() == before
    assert ledger.request_status(req["request_id"]) == "open"
    parent_view = dump(make_service("parent").check_budget())
    assert parent_view["family_cap_cents"] == 40000
    assert dump(make_service("teen").check_budget())["personal_cap_cents"] == 5000


# ---------------------------------------------------------------- L2-08
def test_l2_08_list_orders_own_only_for_teen_all_for_parent(parent, teen, child, ledger):
    teen.place_order(price_cents=1000, **ORDER)
    parent.place_order(price_cents=2000, **ORDER)
    req = dump(child.request_approval(price_cents=500, **ORDER))
    parent.approve_request(request_id=req["request_id"])

    assert {o["member_id"] for o in dump(teen.list_orders())["orders"]} == {"teen"}
    assert {o["member_id"] for o in dump(child.list_orders())["orders"]} == {"child"}
    assert {o["member_id"] for o in dump(parent.list_orders())["orders"]} == {"teen", "parent", "child"}
    assert len(dump(parent.list_orders())["orders"]) == 3
    # requests: own only for the child, all for the parent
    child.request_approval(price_cents=100, **ORDER)
    assert {r["member_id"] for r in dump(child.list_requests())["requests"]} == {"child"}
    assert {r["member_id"] for r in dump(teen.list_requests())["requests"]} <= {"teen"}
    assert len(dump(parent.list_requests())["requests"]) == 1


# ---------------------------------------------------------------- L2-09
def test_l2_09_order_result_fields(teen, ledger):
    r = dump(teen.place_order(price_cents=1234, **ORDER))
    assert r["ok"] is True
    assert isinstance(r["order_id"], int) and r["order_id"] > 0
    assert r["price_cents"] == 1234
    assert r["shop"] == ORDER["shop"]
    assert r["deep_link"] == ORDER["deep_link"]
    assert r["product_name"] == ORDER["product_name"]
    assert r["member_id"] == "teen" and r["month"] == "2026-11"
    assert r["remaining_personal_cents"] == 5000 - 1234
    assert r["remaining_family_cents"] == 40000 - 1234
    assert ledger.orders() == 1



# ---------------------------------------------------------------- MCP layer (in-process)
def _structured(res):
    if isinstance(res, dict):
        return res
    for attr in ("structured_content", "structuredContent"):
        val = getattr(res, attr, None)
        if val:
            return val.get("result", val) if set(val) == {"result"} else val
    for block in getattr(res, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except ValueError:
                return None
    return None


def _call(name, args):
    from family_shopper.wallet import server

    res = asyncio.run(server.mcp.call_tool(name, args))
    return res


def test_l2_01_mcp_layer_in_process_valid_call(tmp_path, clock, monkeypatch):
    from family_shopper.wallet import server

    monkeypatch.setenv("WALLET_DB", str(tmp_path / "mcp.sqlite"))
    monkeypatch.setenv("WALLET_TOKEN_SECRET", SECRET)
    monkeypatch.setattr(server, "_service", None)
    # the real clock is used by the server's default resolver: mint against the real clock
    monkeypatch.setenv("WALLET_MEMBER_TOKEN", mint_token("teen", 600, SECRET))
    res = _call("place_order", {**ORDER, "price_cents": 1500})
    out = _structured(res)
    assert out["ok"] is True and out["price_cents"] == 1500 and out["remaining_personal_cents"] == 3500
    monkeypatch.setattr(server, "_service", None)


def test_l2_02_mcp_layer_wrong_type_never_creates_an_order(tmp_path, monkeypatch):
    import sqlite3

    from family_shopper.wallet import server

    db_file = tmp_path / "mcp2.sqlite"
    monkeypatch.setenv("WALLET_DB", str(db_file))
    monkeypatch.setenv("WALLET_TOKEN_SECRET", SECRET)
    monkeypatch.setattr(server, "_service", None)
    monkeypatch.setenv("WALLET_MEMBER_TOKEN", mint_token("teen", 600, SECRET))
    try:
        res = _call("place_order", {**ORDER, "price_cents": "lots"})
        out = _structured(res)
        refused = isinstance(out, dict) and out.get("ok") is False
        refused = refused or getattr(res, "is_error", False)
    except Exception:  # MCP-layer schema validation may raise: also a refusal
        refused = True
    assert refused
    monkeypatch.setattr(server, "_service", None)
    conn = sqlite3.connect(db_file)
    try:
        try:
            count = conn.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        except sqlite3.OperationalError:
            count = 0  # rejected before the db was even created
        assert count == 0
    finally:
        conn.close()
