# Author:    mikomeller
# Version:   0.1.0
# Filename:  conftest.py
# Pathname:  tests/conftest.py
# Purpose:   Shared fixtures for the wallet tests: temp SQLite db, example config, fake clock, resolvers
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from family_shopper.wallet.db import connect, init_db, load_config
from family_shopper.wallet.identity import Member
from family_shopper.wallet.service import WalletService

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config" / "family_budget.example.yaml"


class FakeClock:
    """Tz-aware clock the tests can move."""

    def __init__(self, now: datetime) -> None:
        self.now = now

    def __call__(self) -> datetime:
        return self.now

    def set(self, now: datetime) -> None:
        self.now = now


class FakeResolver:
    """Resolver that always returns one fixed member."""

    def __init__(self, member: Member) -> None:
        self.member = member

    def resolve(self) -> Member:
        return self.member


def dump(result) -> dict:
    """Service results are Pydantic models (or dicts); tests compare dicts."""
    return result.model_dump() if hasattr(result, "model_dump") else dict(result)


@pytest.fixture
def config() -> dict:
    return load_config(CONFIG_PATH)


@pytest.fixture
def db_path(tmp_path, config) -> Path:
    path = tmp_path / "wallet.sqlite"
    conn = connect(path)
    try:
        init_db(conn, config)
    finally:
        conn.close()
    return path


@pytest.fixture
def clock() -> FakeClock:
    return FakeClock(datetime(2026, 11, 15, 12, 0, tzinfo=UTC))


@pytest.fixture
def members() -> dict[str, Member]:
    return {
        "parent": Member(id="parent", role="parent"),
        "teen": Member(id="teen", role="teen"),
        "child": Member(id="child", role="child"),
    }


@pytest.fixture
def make_service(db_path, clock, members):
    """make_service('teen') -> WalletService whose caller is the teen."""

    def _make(who: str) -> WalletService:
        return WalletService(db_path, FakeResolver(members[who]), clock)

    return _make


@pytest.fixture
def parent(make_service):
    return make_service("parent")


@pytest.fixture
def teen(make_service):
    return make_service("teen")


@pytest.fixture
def child(make_service):
    return make_service("child")


@pytest.fixture
def raw(db_path):
    """Direct sqlite access to assert state and to seed spend."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    yield conn
    conn.close()


class Ledger:
    """Seed spend and count rows directly in the db."""

    def __init__(self, db_path: Path, clock: FakeClock) -> None:
        self.db_path = db_path
        self.clock = clock

    def _exec(self, sql: str, args=()):
        conn = sqlite3.connect(self.db_path)
        try:
            cur = conn.execute(sql, args)
            conn.commit()
            return cur.fetchall()
        finally:
            conn.close()

    def seed_order(self, member_id: str, cents: int, month: str | None = None) -> None:
        month = month or self.clock().astimezone(ZoneInfo("Europe/Berlin")).strftime("%Y-%m")
        self._exec(
            "INSERT INTO orders (member_id, placed_by, product_name, shop, deep_link, price_cents,"
            " month, created_at) VALUES (?,?,?,?,?,?,?,?)",
            (member_id, member_id, "seed", "seed", "https://x.test/seed", cents, month,
             self.clock().isoformat()),
        )

    def orders(self) -> int:
        return self._exec("SELECT COUNT(*) FROM orders")[0][0]

    def requests(self) -> int:
        return self._exec("SELECT COUNT(*) FROM approval_requests")[0][0]

    def spent(self) -> int:
        return self._exec("SELECT COALESCE(SUM(price_cents),0) FROM orders")[0][0]

    def request_status(self, request_id: int) -> str:
        return self._exec("SELECT status FROM approval_requests WHERE id=?", (request_id,))[0][0]

    def state(self) -> tuple:
        return (self.orders(), self.requests(), self.spent())


@pytest.fixture
def ledger(db_path, clock) -> Ledger:
    return Ledger(db_path, clock)


ORDER = {"product_name": "Der Hobbit", "shop": "shop.test", "deep_link": "https://shop.test/p/1"}
