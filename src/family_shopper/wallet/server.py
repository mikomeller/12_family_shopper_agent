"""
Author:    mikomeller
Version:   0.1.2
Filename:  server.py
Pathname:  src/family_shopper/wallet/server.py
Purpose:   Family Wallet MCP stdio server: thin wrapper, one line per tool calling WalletService
"""

from __future__ import annotations

import os

from mcp.server.context import ServerRequestContext
from mcp.server.mcpserver import MCPServer

from family_shopper.wallet import db
from family_shopper.wallet.identity import BorisResolver, TokenResolver, request_meta
from family_shopper.wallet.service import WalletService


def _resolver(path: str | os.PathLike[str]) -> TokenResolver | BorisResolver:
    if os.environ.get("WALLET_IDENTITY_RESOLVER", "token") == "boris":
        return BorisResolver(path)
    return TokenResolver(path)


async def _publish_request_meta(ctx: ServerRequestContext, call_next):
    """Publish the inbound request's `_meta` so BorisResolver can read the verified caller identity."""
    with request_meta(ctx.meta):
        return await call_next(ctx)


mcp = MCPServer("family-wallet", middleware=[_publish_request_meta])
_service: WalletService | None = None


def service() -> WalletService:
    global _service
    if _service is None:
        path = db.default_db_path()
        conn = db.connect(path)
        try:
            db.init_db(conn, db.load_config())
        finally:
            conn.close()
        _service = WalletService(path, _resolver(path))
    return _service


@mcp.tool()
def check_budget(price_cents: int | None = None) -> dict:
    """Show the caller's remaining personal and family budget this month; optionally test a price."""
    return service().check_budget(price_cents).model_dump()


@mcp.tool()
def place_order(product_name: str, shop: str, deep_link: str, price_cents: int) -> dict:
    """Record a simulated order (no payment) if the personal and family caps allow it."""
    return service().place_order(product_name, shop, deep_link, price_cents).model_dump()


@mcp.tool()
def request_approval(product_name: str, shop: str, deep_link: str, price_cents: int) -> dict:
    """Child only: ask a parent to approve an order."""
    return service().request_approval(product_name, shop, deep_link, price_cents).model_dump()


@mcp.tool()
def approve_request(request_id: int) -> dict:
    """Parent only: approve an open request and record the order."""
    return service().approve_request(request_id).model_dump()


@mcp.tool()
def reject_request(request_id: int) -> dict:
    """Parent only: reject an open request; no order is created."""
    return service().reject_request(request_id).model_dump()


@mcp.tool()
def set_budget(target: str, cap_cents: int | None) -> dict:
    """Parent only: set the cap in cents for 'family' or a member id."""
    return service().set_budget(target, cap_cents).model_dump()


@mcp.tool()
def list_orders(month: str | None = None) -> dict:
    """List orders of a month (YYYY-MM, default current); parents see all, others only their own."""
    return service().list_orders(month).model_dump()


@mcp.tool()
def list_requests(status: str | None = "open") -> dict:
    """List approval requests (open, approved, rejected or all); parents see all, others their own."""
    return service().list_requests(status).model_dump()


if __name__ == "__main__":
    mcp.run("stdio")
