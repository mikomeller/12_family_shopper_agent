# Author:    c666agent666
# Version:   0.1.1
# Filename:  test_boris_identity.py
# Pathname:  tests/test_boris_identity.py
# Purpose:   BorisResolver: resolves the TrustBoris-forwarded caller identity and fails closed
from __future__ import annotations

import asyncio

import pytest
from conftest import ORDER, dump

from family_shopper.wallet.identity import (
    AGENT_IDENTITY_KEY,
    AGENT_IDENTITY_LEGACY_KEY,
    BorisResolver,
    request_meta,
)
from family_shopper.wallet.service import WalletService


@pytest.fixture
def boris_service(db_path, clock):
    return WalletService(db_path, BorisResolver(db_path), clock)


def test_boris_resolves_subject_to_member(boris_service):
    with request_meta({AGENT_IDENTITY_KEY: "teen"}):
        r = dump(boris_service.check_budget())
    assert r["ok"] is True and r["member_id"] == "teen" and r["role"] == "teen"


def test_boris_legacy_key_resolves(boris_service):
    with request_meta({AGENT_IDENTITY_LEGACY_KEY: "child"}):
        r = dump(boris_service.check_budget())
    assert r["ok"] is True and r["member_id"] == "child" and r["role"] == "child"


def test_boris_dict_subject_resolves(boris_service):
    with request_meta({AGENT_IDENTITY_KEY: {"sub": "parent"}}):
        r = dump(boris_service.check_budget())
    assert r["ok"] is True and r["member_id"] == "parent" and r["personal_cap_cents"] is None


def test_boris_missing_meta_fails_closed(boris_service, ledger):
    r = dump(boris_service.place_order(price_cents=100, **ORDER))
    assert r["ok"] is False and r["error_code"] == "IDENTITY_MISSING"
    assert ledger.state() == (0, 0, 0)


def test_boris_unknown_subject_fails_closed(boris_service, ledger):
    with request_meta({AGENT_IDENTITY_KEY: "ghost"}):
        r = dump(boris_service.place_order(price_cents=100, **ORDER))
    assert r["ok"] is False and r["error_code"] == "IDENTITY_INVALID"
    assert ledger.state() == (0, 0, 0)


def test_boris_garbage_value_fails_closed(boris_service):
    with request_meta({AGENT_IDENTITY_KEY: {"foo": "bar"}}):
        r = dump(boris_service.check_budget())
    assert r["ok"] is False and r["error_code"] == "IDENTITY_INVALID"


def test_boris_teen_cap_enforced(boris_service, ledger):
    with request_meta({AGENT_IDENTITY_KEY: "teen"}):
        over = dump(boris_service.place_order(price_cents=5001, **ORDER))
        ok = dump(boris_service.place_order(price_cents=4000, **ORDER))
    assert over["ok"] is False and over["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert ok["ok"] is True and ok["member_id"] == "teen"
    assert ledger.orders() == 1


def test_boris_child_orders_within_budget_and_requests_above_it(boris_service, ledger):
    # Owner decision 2026-11-27: up to the child's budget (2000 cents) the wallet decides; above it a parent steps in.
    with request_meta({AGENT_IDENTITY_KEY: "child"}):
        ok = dump(boris_service.place_order(price_cents=100, **ORDER))
        refused = dump(boris_service.place_order(price_cents=2000, **ORDER))
        req = dump(boris_service.request_approval(price_cents=2000, **ORDER))
    assert ok["ok"] is True and ok["member_id"] == "child"
    assert refused["ok"] is False and refused["error_code"] == "PERSONAL_CAP_EXCEEDED"
    assert req["ok"] is True and req["member_id"] == "child"
    assert ledger.requests() == 1 and ledger.orders() == 1


def test_boris_parent_approves_child_request(boris_service, ledger):
    with request_meta({AGENT_IDENTITY_KEY: "child"}):
        req = dump(boris_service.request_approval(price_cents=500, **ORDER))
    with request_meta({AGENT_IDENTITY_KEY: "parent"}):
        ap = dump(boris_service.approve_request(request_id=req["request_id"]))
    assert ap["ok"] is True and ap["approved_by"] == "parent" and ap["member_id"] == "child"
    assert ledger.orders() == 1


def test_middleware_publishes_and_resets_meta():
    from family_shopper.wallet import server
    from family_shopper.wallet.identity import _request_meta

    seen = {}

    async def call_next(_ctx):
        seen["during"] = _request_meta.get()

    class FakeCtx:
        meta = {AGENT_IDENTITY_KEY: "teen"}

    async def run():
        await server._publish_request_meta(FakeCtx(), call_next)
        seen["after"] = _request_meta.get()

    asyncio.run(run())
    assert seen["during"] == {AGENT_IDENTITY_KEY: "teen"}
    assert seen["after"] is None


def test_resolver_selection(monkeypatch):
    from family_shopper.wallet import server
    from family_shopper.wallet.identity import TokenResolver

    monkeypatch.setenv("WALLET_IDENTITY_RESOLVER", "boris")
    assert isinstance(server._resolver("x.db"), BorisResolver)
    monkeypatch.setenv("WALLET_IDENTITY_RESOLVER", "token")
    assert isinstance(server._resolver("x.db"), TokenResolver)
    monkeypatch.delenv("WALLET_IDENTITY_RESOLVER", raising=False)
    assert isinstance(server._resolver("x.db"), TokenResolver)
