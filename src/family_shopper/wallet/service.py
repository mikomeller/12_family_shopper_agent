"""
Author:    mikomeller
Version:   0.2.1
Filename:  service.py
Pathname:  src/family_shopper/wallet/service.py
Purpose:   WalletService: one method per tool, caps and roles, BEGIN IMMEDIATE writes; no MCP imports
"""

from __future__ import annotations

import os
import sqlite3
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from family_shopper.wallet import db
from family_shopper.wallet.identity import IdentityInvalid, IdentityMissing, IdentityResolver, Member

Clock = Callable[[], datetime]
BERLIN = ZoneInfo("Europe/Berlin")
MAX_TEXT = 500
ASK_ROLES = ("child", "teen")  # roles that can ask a parent to step in above their own budget
INTERNAL = "The wallet could not complete the request; nothing was changed."


def _utc_now() -> datetime:
    return datetime.now(UTC)


def fmt_eur(cents: int) -> str:
    return f"{cents // 100}.{cents % 100:02d} €"


# ---------------------------------------------------------------- result models
class Refusal(BaseModel):
    ok: Literal[False] = False
    error_code: str
    reason: str
    remaining_personal_cents: int | None = None
    remaining_family_cents: int | None = None


class BudgetResult(BaseModel):
    ok: Literal[True] = True
    member_id: str
    role: str
    month: str
    personal_cap_cents: int | None
    personal_spent_cents: int
    remaining_personal_cents: int | None
    family_cap_cents: int
    family_spent_cents: int
    remaining_family_cents: int
    needs_approval: bool
    fits: bool | None


class OrderResult(BaseModel):
    ok: Literal[True] = True
    order_id: int
    member_id: str
    product_name: str
    shop: str
    deep_link: str
    price_cents: int
    month: str
    remaining_personal_cents: int | None
    remaining_family_cents: int


class ApprovedOrderResult(OrderResult):
    request_id: int
    approved_by: str


class RequestResult(BaseModel):
    ok: Literal[True] = True
    request_id: int
    status: Literal["open"] = "open"
    member_id: str
    price_cents: int
    remaining_personal_cents: int | None
    remaining_family_cents: int


class RejectedResult(BaseModel):
    ok: Literal[True] = True
    request_id: int
    status: Literal["rejected"] = "rejected"
    member_id: str
    product_name: str
    price_cents: int
    rejected_by: str


class BudgetSetResult(BaseModel):
    ok: Literal[True] = True
    target: str
    cap_cents: int | None


class OrderRow(BaseModel):
    order_id: int
    member_id: str
    placed_by: str
    product_name: str
    shop: str
    deep_link: str
    price_cents: int
    created_at: str
    request_id: int | None


class OrdersResult(BaseModel):
    ok: Literal[True] = True
    month: str
    orders: list[OrderRow]


class RequestRow(BaseModel):
    request_id: int
    member_id: str
    product_name: str
    shop: str
    deep_link: str
    price_cents: int
    status: str
    created_at: str


class RequestsResult(BaseModel):
    ok: Literal[True] = True
    requests: list[RequestRow]


class Refuse(Exception):
    def __init__(self, code: str, reason: str, remaining_for: str | None = None) -> None:
        super().__init__(reason)
        self.code, self.reason, self.remaining_for = code, reason, remaining_for


# ---------------------------------------------------------------- validation
def _text(field: str, value: Any) -> str:
    if value is None:
        raise Refuse("INVALID_INPUT", f"Invalid input: {field} is missing.")
    if not isinstance(value, str):
        raise Refuse("INVALID_INPUT", f"Invalid input: {field} has the wrong type.")
    if not value.strip():
        raise Refuse("INVALID_INPUT", f"Invalid input: {field} is empty.")
    if len(value) > MAX_TEXT:
        raise Refuse("INVALID_INPUT", f"Invalid input: {field} is too long.")
    return value


def _amount(value: Any, *, allow_zero: bool = False) -> int:
    ok = isinstance(value, int) and not isinstance(value, bool) and (value >= 0 if allow_zero else value > 0)
    if not ok:
        raise Refuse("INVALID_AMOUNT", "The amount must be a whole number of cents greater than zero.")
    return value


def _order_fields(shop_args: tuple[Any, Any, Any, Any]) -> tuple[str, str, str, int]:
    name, shop, link, price = shop_args
    return _text("product_name", name), _text("shop", shop), _text("deep_link", link), _amount(price)


class WalletService:
    def __init__(
        self,
        db_path: str | os.PathLike[str],
        resolver: IdentityResolver,
        clock: Clock = _utc_now,
    ) -> None:
        self.db_path = db_path
        self.resolver = resolver
        self.clock = clock

    # ------------------------------------------------------------ helpers
    def _month(self) -> str:
        return self.clock().astimezone(BERLIN).strftime("%Y-%m")

    def _now_iso(self) -> str:
        return self.clock().astimezone(UTC).isoformat()

    @staticmethod
    def _spent(conn: sqlite3.Connection, month: str, member_id: str | None = None) -> int:
        if member_id is None:
            q, a = "SELECT COALESCE(SUM(price_cents),0) FROM orders WHERE month=?", (month,)
        else:
            q = "SELECT COALESCE(SUM(price_cents),0) FROM orders WHERE month=? AND member_id=?"
            a = (month, member_id)
        return int(conn.execute(q, a).fetchone()[0])

    def _state(self, conn: sqlite3.Connection, month: str, member_id: str) -> dict[str, Any]:
        m = conn.execute("SELECT role, personal_cap_cents FROM members WHERE id=?", (member_id,)).fetchone()
        fam = int(conn.execute("SELECT family_cap_cents FROM family WHERE id=1").fetchone()[0])
        p_spent = self._spent(conn, month, member_id)
        f_spent = self._spent(conn, month)
        p_cap = m["personal_cap_cents"]
        return {
            "role": m["role"],
            "p_cap": p_cap,
            "p_spent": p_spent,
            "p_rem": None if p_cap is None else max(0, p_cap - p_spent),
            "f_cap": fam,
            "f_spent": f_spent,
            "f_rem": max(0, fam - f_spent),
        }

    def _check_caps(
        self, conn: sqlite3.Connection, month: str, member_id: str, price: int, *, personal: bool = True
    ) -> dict[str, Any]:
        s = self._state(conn, month, member_id)
        if personal and s["p_cap"] is not None and s["p_spent"] + price > s["p_cap"]:
            hint = " A parent can step in: use request_approval." if s["role"] in ASK_ROLES else ""
            raise Refuse(
                "PERSONAL_CAP_EXCEEDED",
                f"This exceeds {member_id}'s monthly limit; {fmt_eur(s['p_rem'])} left this month.{hint}",
                member_id,
            )
        if s["f_spent"] + price > s["f_cap"]:
            raise Refuse(
                "FAMILY_CAP_EXCEEDED",
                f"This exceeds the family's monthly limit; {fmt_eur(s['f_rem'])} left this month.",
                member_id,
            )
        return s

    def _refusal(self, e: Refuse, caller_id: str | None) -> Refusal:
        r = Refusal(error_code=e.code, reason=e.reason)
        who = e.remaining_for or caller_id
        if who is None:
            return r
        try:
            conn = db.connect(self.db_path)
            try:
                s = self._state(conn, self._month(), who)
            finally:
                conn.close()
            r.remaining_personal_cents, r.remaining_family_cents = s["p_rem"], s["f_rem"]
        except Exception:
            pass
        return r

    def _run(
        self, body: Callable[[sqlite3.Connection, Member, str], BaseModel]
    ) -> dict[str, Any] | BaseModel:
        caller_id: str | None = None
        try:
            try:
                resolved = self.resolver.resolve()
            except IdentityMissing:
                return Refusal(error_code="IDENTITY_MISSING", reason="No caller identity was provided.")
            except IdentityInvalid:
                return Refusal(
                    error_code="IDENTITY_INVALID", reason="The caller identity is invalid or expired."
                )
            conn = db.connect(self.db_path)
            try:
                row = conn.execute("SELECT id, role FROM members WHERE id=?", (resolved.id,)).fetchone()
                if row is None:
                    return Refusal(
                        error_code="IDENTITY_INVALID", reason="The caller identity is invalid or expired."
                    )
                caller = Member(id=row["id"], role=row["role"])
                caller_id = caller.id
                try:
                    return body(conn, caller, self._month())
                finally:
                    if conn.in_transaction:
                        conn.execute("ROLLBACK")
                    conn.close()
            except Refuse as e:
                return self._refusal(e, caller_id)
        except Exception:
            return Refusal(error_code="INTERNAL_ERROR", reason=INTERNAL)

    # ------------------------------------------------------------ tools
    def check_budget(self, price_cents: int | None = None) -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, month: str) -> BaseModel:
            if price_cents is not None:
                _amount(price_cents)
            s = self._state(conn, month, caller.id)
            fits = None
            if price_cents is not None:
                fits = (s["p_rem"] is None or price_cents <= s["p_rem"]) and price_cents <= s["f_rem"]
            needs_approval = (
                caller.role in ASK_ROLES
                and price_cents is not None
                and s["p_rem"] is not None
                and price_cents > s["p_rem"]
                and price_cents <= s["f_rem"]
            )
            return BudgetResult(
                member_id=caller.id,
                role=caller.role,
                month=month,
                personal_cap_cents=s["p_cap"],
                personal_spent_cents=s["p_spent"],
                remaining_personal_cents=s["p_rem"],
                family_cap_cents=s["f_cap"],
                family_spent_cents=s["f_spent"],
                remaining_family_cents=s["f_rem"],
                needs_approval=needs_approval,
                fits=fits,
            )

        return self._run(body)

    def place_order(self, product_name: str, shop: str, deep_link: str, price_cents: int) -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, month: str) -> BaseModel:
            name, shp, link, price = _order_fields((product_name, shop, deep_link, price_cents))
            conn.execute("BEGIN IMMEDIATE")
            self._check_caps(conn, month, caller.id, price)
            oid = self._insert_order(conn, caller.id, caller.id, None, name, shp, link, price, month)
            s = self._state(conn, month, caller.id)
            conn.execute("COMMIT")
            return OrderResult(
                order_id=oid, member_id=caller.id, product_name=name, shop=shp, deep_link=link,
                price_cents=price, month=month,
                remaining_personal_cents=s["p_rem"], remaining_family_cents=s["f_rem"],
            )  # fmt: skip

        return self._run(body)

    def _insert_order(self, conn, member_id, placed_by, request_id, name, shop, link, price, month) -> int:  # noqa: ANN001
        cur = conn.execute(
            "INSERT INTO orders (member_id, placed_by, request_id,"
            " product_name, shop, deep_link, price_cents,"
            " month, created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (member_id, placed_by, request_id, name, shop, link, price, month, self._now_iso()),
        )
        return int(cur.lastrowid)

    def request_approval(self, product_name: str, shop: str, deep_link: str, price_cents: int) -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, month: str) -> BaseModel:
            name, shp, link, price = _order_fields((product_name, shop, deep_link, price_cents))
            if caller.role not in ASK_ROLES:
                raise Refuse("NOT_ALLOWED_FOR_ROLE", f"{caller.id} can order directly; use place_order.")
            conn.execute("BEGIN IMMEDIATE")
            cur = conn.execute(
                "INSERT INTO approval_requests (member_id, product_name, shop, deep_link,"
                " price_cents, status,"
                " created_at) VALUES (?,?,?,?,?, 'open', ?)",
                (caller.id, name, shp, link, price, self._now_iso()),
            )
            rid = int(cur.lastrowid)
            s = self._state(conn, month, caller.id)
            conn.execute("COMMIT")
            return RequestResult(
                request_id=rid, member_id=caller.id, price_cents=price,
                remaining_personal_cents=s["p_rem"], remaining_family_cents=s["f_rem"],
            )  # fmt: skip

        return self._run(body)

    def approve_request(self, request_id: int) -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, month: str) -> BaseModel:
            if request_id is None:
                raise Refuse("INVALID_INPUT", "Invalid input: request_id is missing.")
            if not isinstance(request_id, int) or isinstance(request_id, bool):
                raise Refuse("INVALID_INPUT", "Invalid input: request_id has the wrong type.")
            if caller.role != "parent":
                raise Refuse("NOT_A_PARENT", "Only a parent can approve requests.")
            conn.execute("BEGIN IMMEDIATE")
            req = conn.execute("SELECT * FROM approval_requests WHERE id=?", (request_id,)).fetchone()
            if req is None:
                raise Refuse("REQUEST_NOT_FOUND", f"Approval request {request_id} does not exist.")
            if req["status"] != "open":
                raise Refuse("REQUEST_NOT_OPEN", f"Approval request {request_id} is already {req['status']}.")
            # Approved by a parent (checked above): family cap only, whatever the requester's role.
            # The order still counts as the requester's spending (remaining is floored at 0).
            self._check_caps(conn, month, req["member_id"], req["price_cents"], personal=False)
            oid = self._insert_order(
                conn, req["member_id"], caller.id, request_id, req["product_name"], req["shop"],
                req["deep_link"], req["price_cents"], month,
            )  # fmt: skip
            conn.execute(
                "UPDATE approval_requests SET status='approved', decided_at=?, decided_by=?"
                " WHERE id=? AND status='open'",
                (self._now_iso(), caller.id, request_id),
            )
            s = self._state(conn, month, req["member_id"])
            conn.execute("COMMIT")
            return ApprovedOrderResult(
                order_id=oid, member_id=req["member_id"], product_name=req["product_name"], shop=req["shop"],
                deep_link=req["deep_link"], price_cents=req["price_cents"], month=month,
                remaining_personal_cents=s["p_rem"], remaining_family_cents=s["f_rem"],
                request_id=request_id, approved_by=caller.id,
            )  # fmt: skip

        return self._run(body)

    def reject_request(self, request_id: int) -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, month: str) -> BaseModel:
            if request_id is None:
                raise Refuse("INVALID_INPUT", "Invalid input: request_id is missing.")
            if not isinstance(request_id, int) or isinstance(request_id, bool):
                raise Refuse("INVALID_INPUT", "Invalid input: request_id has the wrong type.")
            if caller.role != "parent":
                raise Refuse("NOT_A_PARENT", "Only a parent can reject requests.")
            conn.execute("BEGIN IMMEDIATE")
            req = conn.execute("SELECT * FROM approval_requests WHERE id=?", (request_id,)).fetchone()
            if req is None:
                raise Refuse("REQUEST_NOT_FOUND", f"Approval request {request_id} does not exist.")
            if req["status"] != "open":
                raise Refuse("REQUEST_NOT_OPEN", f"Approval request {request_id} is already {req['status']}.")
            conn.execute(
                "UPDATE approval_requests SET status='rejected', decided_at=?, decided_by=?"
                " WHERE id=? AND status='open'",
                (self._now_iso(), caller.id, request_id),
            )
            conn.execute("COMMIT")
            return RejectedResult(
                request_id=request_id, member_id=req["member_id"], product_name=req["product_name"],
                price_cents=req["price_cents"], rejected_by=caller.id,
            )  # fmt: skip

        return self._run(body)

    def set_budget(self, target: str, cap_cents: int | None) -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, month: str) -> BaseModel:
            tgt = _text("target", target)
            if cap_cents is not None:
                _amount(cap_cents, allow_zero=True)
            if caller.role != "parent":
                raise Refuse("NOT_A_PARENT", "Only a parent can set budgets.")
            conn.execute("BEGIN IMMEDIATE")
            if tgt == "family":
                if cap_cents is None:
                    _amount(cap_cents)
                conn.execute("UPDATE family SET family_cap_cents=? WHERE id=1", (cap_cents,))
            else:
                m = conn.execute("SELECT role FROM members WHERE id=?", (tgt,)).fetchone()
                if m is None:
                    raise Refuse("MEMBER_NOT_FOUND", f"Member {tgt} does not exist.")
                if cap_cents is None and m["role"] != "parent":
                    _amount(cap_cents)
                conn.execute("UPDATE members SET personal_cap_cents=? WHERE id=?", (cap_cents, tgt))
            conn.execute("COMMIT")
            return BudgetSetResult(target=tgt, cap_cents=cap_cents)

        return self._run(body)

    def list_orders(self, month: str | None = None) -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, cur_month: str) -> BaseModel:
            mo = cur_month if month is None else _text("month", month)
            if month is not None and not (
                len(mo) == 7 and mo[4] == "-" and mo[:4].isdigit() and mo[5:].isdigit()
            ):
                raise Refuse("INVALID_INPUT", "Invalid input: month must look like YYYY-MM.")
            q = "SELECT * FROM orders WHERE month=?"
            args: list[Any] = [mo]
            if caller.role != "parent":
                q += " AND member_id=?"
                args.append(caller.id)
            rows = conn.execute(q + " ORDER BY id", args).fetchall()
            return OrdersResult(
                month=mo,
                orders=[
                    OrderRow(
                        order_id=r["id"], member_id=r["member_id"], placed_by=r["placed_by"],
                        product_name=r["product_name"], shop=r["shop"], deep_link=r["deep_link"],
                        price_cents=r["price_cents"], created_at=r["created_at"], request_id=r["request_id"],
                    )
                    for r in rows
                ],
            )  # fmt: skip

        return self._run(body)

    def list_requests(self, status: str | None = "open") -> BaseModel:
        def body(conn: sqlite3.Connection, caller: Member, month: str) -> BaseModel:
            if status is not None and status not in ("open", "approved", "rejected"):
                raise Refuse(
                    "INVALID_INPUT", "Invalid input: status must be 'open', 'approved' or 'rejected'."
                )
            q, args = "SELECT * FROM approval_requests WHERE 1=1", []
            if status is not None:
                q += " AND status=?"
                args.append(status)
            if caller.role != "parent":
                q += " AND member_id=?"
                args.append(caller.id)
            rows = conn.execute(q + " ORDER BY id", args).fetchall()
            return RequestsResult(
                requests=[
                    RequestRow(
                        request_id=r["id"], member_id=r["member_id"], product_name=r["product_name"],
                        shop=r["shop"], deep_link=r["deep_link"], price_cents=r["price_cents"],
                        status=r["status"], created_at=r["created_at"],
                    )
                    for r in rows
                ]
            )  # fmt: skip

        return self._run(body)
