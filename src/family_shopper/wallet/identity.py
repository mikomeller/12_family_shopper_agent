"""
Author:    mikomeller
Version:   0.1.0
Filename:  identity.py
Pathname:  src/family_shopper/wallet/identity.py
Purpose:   Caller identity: Member, IdentityResolver, HMAC TokenResolver, mint_token
"""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

from family_shopper.wallet import db

Role = Literal["parent", "teen", "child"]
Clock = Callable[[], datetime]


class IdentityMissing(Exception):
    """No caller identity was provided."""


class IdentityInvalid(Exception):
    """The caller identity is invalid or expired."""


@dataclass(frozen=True)
class Member:
    id: str
    role: Role


class IdentityResolver(Protocol):
    def resolve(self) -> Member: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _sign(secret: str, member_id: str, expiry: int) -> str:
    return hmac.new(secret.encode(), f"{member_id}.{expiry}".encode(), hashlib.sha256).hexdigest()


def mint_token(member_id: str, ttl_s: int, secret: str, clock: Clock = _utc_now) -> str:
    expiry = int(clock().timestamp()) + int(ttl_s)
    return f"{member_id}.{expiry}.{_sign(secret, member_id, expiry)}"


class TokenResolver:
    """Reads WALLET_MEMBER_TOKEN on every call and verifies it with WALLET_TOKEN_SECRET (fail closed)."""

    def __init__(self, db_path: str | os.PathLike[str], clock: Clock = _utc_now) -> None:
        self._db_path = db_path
        self._clock = clock

    def resolve(self) -> Member:
        token = os.environ.get("WALLET_MEMBER_TOKEN", "")
        if not token.strip():
            raise IdentityMissing
        secret = os.environ.get("WALLET_TOKEN_SECRET", "")
        parts = token.strip().split(".")
        if not secret or len(parts) != 3:
            raise IdentityInvalid
        member_id, expiry_s, signature = parts
        try:
            expiry = int(expiry_s)
        except ValueError:
            raise IdentityInvalid from None
        if not hmac.compare_digest(signature, _sign(secret, member_id, expiry)):
            raise IdentityInvalid
        if expiry <= int(self._clock().timestamp()):
            raise IdentityInvalid
        if str(self._db_path) != ":memory:" and not Path(self._db_path).exists():
            raise IdentityInvalid
        conn = db.connect(self._db_path)
        try:
            row = conn.execute("SELECT id, role FROM members WHERE id = ?", (member_id,)).fetchone()
        except Exception:
            raise IdentityInvalid from None
        finally:
            conn.close()
        if row is None:
            raise IdentityInvalid
        return Member(id=row["id"], role=row["role"])
