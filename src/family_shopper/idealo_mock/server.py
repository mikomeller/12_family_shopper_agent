# Author:    mikomeller
# Version:   0.1.1
# Filename:  server.py
# Pathname:  src/family_shopper/idealo_mock/server.py
# Purpose:   Offline MCP server "idealo-mock": four read-only idealo-style tools + check_discount
"""Offline idealo mock MCP server.

UNVERIFIED: the response shapes of the real idealo MCP have not been recorded yet; the shapes here
are invented to match the four tool names and the facts in doc/research/affinidi_boris_idealo.md.
All shops and data are fake. One fixture (backpack-inj) carries a prompt injection in `description`
as plain data, to test screening. Start: `uv run python -m family_shopper.idealo_mock.server`.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from functools import cache
from importlib import resources
from typing import Any

from mcp.server.mcpserver import MCPServer

from family_shopper.discount_check import PricePoint, check_discount

MAX_OFFERS = 5


@cache
def _products() -> dict[str, dict[str, Any]]:
    text = resources.files("family_shopper.idealo_mock").joinpath("fixtures/products.json").read_text("utf-8")
    return {p["product_ref"]: p for p in json.loads(text)["products"]}


def _get(product_ref: str) -> dict[str, Any] | None:
    return _products().get(product_ref)


def _not_found(product_ref: str) -> dict[str, Any]:
    return {"error": f"unknown product_ref: {product_ref}"}


def search_products_impl(query: str, country: str = "DE") -> dict[str, Any]:
    words = query.lower().split()
    hits = [
        {"product_ref": p["product_ref"], "title": p["title"], "category": p["category"]}
        for p in _products().values()
        if all(w in p["title"].lower() for w in words)
    ]
    return {"country": country, "results": hits}


def get_product_details_impl(product_ref: str) -> dict[str, Any]:
    p = _get(product_ref)
    if p is None:
        return _not_found(product_ref)
    keys = ("product_ref", "title", "description", "category", "advertised_was_cents")
    out = {k: p[k] for k in keys}
    out.update({k: p[k] for k in ("brand", "ean", "country", "currency", "advertised_by") if k in p})
    return out


def get_product_offers_impl(product_ref: str) -> dict[str, Any]:
    p = _get(product_ref)
    if p is None:
        return _not_found(product_ref)
    offers = [{**o, "total_cents": o["price_cents"] + o["shipping_cents"]} for o in p["offers"]]
    offers.sort(key=lambda o: o["total_cents"])
    return {"product_ref": product_ref, "offers": [_offer(o) for o in offers[:MAX_OFFERS]]}


def _offer(o: dict[str, Any]) -> dict[str, Any]:
    keys = ("shop", "price_cents", "shipping_cents", "total_cents", "deep_link")
    out = {k: o[k] for k in keys}
    out.update({k: o[k] for k in ("delivery_days", "availability", "shop_note") if k in o})
    return out


def get_product_price_history_impl(product_ref: str) -> dict[str, Any]:
    p = _get(product_ref)
    if p is None:
        return _not_found(product_ref)
    return {"product_ref": product_ref, "history": p["history"]}


def check_discount_impl(
    sale_price_cents: int,
    claimed_was_cents: int | None,
    history: list[dict[str, int]],
    sale_days: int = 0,
    best_offer_cents: int | None = None,
) -> dict[str, Any]:
    try:
        points = [PricePoint(int(h["days_ago"]), int(h["price_cents"])) for h in history]
    except (KeyError, TypeError, ValueError):
        points = [PricePoint(-1, 0)]  # malformed point -> INVALID_INPUT from the pure function
    result = check_discount(sale_price_cents, claimed_was_cents, points, sale_days, best_offer_cents)
    out = asdict(result)
    out["verdict"] = result.verdict.value
    return out


mcp = MCPServer("idealo-mock")


@mcp.tool()
def search_products(query: str, country: str = "DE") -> dict[str, Any]:
    """Search products by title words (read-only, fixture data)."""
    return search_products_impl(query, country)


@mcp.tool()
def get_product_details(product_ref: str) -> dict[str, Any]:
    """Details of one product (read-only, fixture data)."""
    return get_product_details_impl(product_ref)


@mcp.tool()
def get_product_offers(product_ref: str) -> dict[str, Any]:
    """Up to 5 offers, cheapest total (price + shipping) first (read-only)."""
    return get_product_offers_impl(product_ref)


@mcp.tool()
def get_product_price_history(product_ref: str) -> dict[str, Any]:
    """30 daily lowest-price points: days_ago, price_cents (read-only)."""
    return get_product_price_history_impl(product_ref)


@mcp.tool(name="check_discount")
def check_discount_tool(
    sale_price_cents: int,
    claimed_was_cents: int | None,
    history: list[dict[str, int]],
    sale_days: int = 0,
    best_offer_cents: int | None = None,
) -> dict[str, Any]:
    """Is the advertised discount real? Pure deterministic check, never places an order."""
    return check_discount_impl(sale_price_cents, claimed_was_cents, history, sale_days, best_offer_cents)


if __name__ == "__main__":
    mcp.run("stdio")
