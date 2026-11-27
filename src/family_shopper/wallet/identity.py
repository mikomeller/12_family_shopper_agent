"""
Author:    mikomeller
Version:   0.1.1
Filename:  identity.py
Pathname:  src/family_shopper/wallet/identity.py
Purpose:   Caller identity: Member, IdentityResolver, HMAC TokenResolver, BorisResolver, mint_token
"""

from __future__ import annotations

import hashlib
import hmac
import os
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal, Protocol

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


AGENT_IDENTITY_KEY = "io.affinidi.fabric/agent-identity"
AGENT_IDENTITY_LEGACY_KEY = "https://fabric.affinidi.io/extensions/agent-identity/v1"

_request_meta: ContextVar[Mapping[str, Any] | None] = ContextVar("boris_request_meta", default=None)


@contextmanager
def request_meta(meta: Mapping[str, Any] | None) -> Iterator[None]:
    """Publish the current MCP request's `_meta` for BorisResolver; reset on exit."""
    token = _request_meta.set(dict(meta) if meta else None)
    try:
        yield
    finally:
        _request_meta.reset(token)


def _subject_of(raw: Any) -> str | None:
    """The verified caller subject: a plain string, or a mapping's sub/subject/member_id/id."""
    if isinstance(raw, str):
        return raw.strip() or None
    if isinstance(raw, Mapping):
        for key in ("sub", "subject", "member_id", "id"):
            value = raw.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    return None


class BorisResolver:
    """Resolve the caller from the verified identity Boris's gateway forwards in the request `_meta`
    (canonical `io.affinidi.fabric/agent-identity`, legacy `https://fabric.affinidi.io/extensions/agent-identity/v1`).

    The forwarded identity's subject must equal a member id in `members`; a missing or unknown
    identity fails closed (IdentityMissing / IdentityInvalid).
    """

    def __init__(self, db_path: str | os.PathLike[str]) -> None:
        self._db_path = db_path

    def resolve(self) -> Member:
        meta = _request_meta.get()
        if not meta:
            raise IdentityMissing
        subject = _subject_of(meta.get(AGENT_IDENTITY_KEY, meta.get(AGENT_IDENTITY_LEGACY_KEY)))
        if subject is None:
            raise IdentityInvalid
        if str(self._db_path) != ":memory:" and not Path(self._db_path).exists():
            raise IdentityInvalid
        conn = db.connect(self._db_path)
        try:
            row = conn.execute("SELECT id, role FROM members WHERE id = ?", (subject,)).fetchone()
        except Exception:
            raise IdentityInvalid from None
        finally:
            conn.close()
        if row is None:
            raise IdentityInvalid
        return Member(id=row["id"], role=row["role"])
