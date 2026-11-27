# Author:    mikomeller
# Version:   0.1.0
# Filename:  discount_check.py
# Pathname:  src/family_shopper/discount_check.py
# Purpose:   Pure integer-only "is this discount real?" checker (#25), see doc/design/discount_check.md
"""Deterministic discount honesty check. No I/O, no floats."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

TOLERANCE_BP = 100
MIN_HISTORY_POINTS = 7
WINDOW_DAYS = 30


class Verdict(StrEnum):
    GENUINE = "GENUINE"
    INFLATED = "INFLATED"
    NOT_BEST_PRICE = "NOT_BEST_PRICE"
    NO_DISCOUNT_CLAIMED = "NO_DISCOUNT_CLAIMED"
    INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INVALID_INPUT = "INVALID_INPUT"


@dataclass(frozen=True)
class PricePoint:
    days_ago: int
    price_cents: int


@dataclass(frozen=True)
class DiscountCheckResult:
    verdict: Verdict
    reason: str
    reference_low_cents: int | None
    claimed_discount_bp: int | None
    real_discount_bp: int | None
    history_points_used: int
    cheaper_elsewhere: bool


def _invalid(reason: str) -> DiscountCheckResult:
    return DiscountCheckResult(Verdict.INVALID_INPUT, f"invalid input: {reason}", None, None, None, 0, False)


def _validate(
    sale: int, was: int | None, history: list[PricePoint], sale_days: int, best: int | None
) -> str | None:
    if sale <= 0:
        return "sale_price_cents must be > 0"
    if was is not None and was <= 0:
        return "claimed_was_cents must be > 0"
    if was is not None and was < sale:
        return "claimed_was_cents must be >= sale_price_cents"
    if sale_days < 0:
        return "sale_days must be >= 0"
    for p in history:
        if p.days_ago < 0:
            return "history days_ago must be >= 0"
        if p.price_cents <= 0:
            return "history price_cents must be > 0"
    if best is not None and best <= 0:
        return "best_offer_cents must be > 0"
    return None


def check_discount(
    sale_price_cents: int,
    claimed_was_cents: int | None,
    history: list[PricePoint],
    sale_days: int = 0,
    best_offer_cents: int | None = None,
) -> DiscountCheckResult:
    sale, was, best = sale_price_cents, claimed_was_cents, best_offer_cents
    err = _validate(sale, was, history, sale_days, best)
    if err:
        return _invalid(err)

    window = [p.price_cents for p in history if sale_days < p.days_ago <= WINDOW_DAYS]
    n = len(window)
    ref: int | None = None
    real_bp: int | None = None
    if n >= MIN_HISTORY_POINTS:
        ref = min(window)
        real_bp = max(0, (ref - sale) * 10000 // ref)
    claimed_bp = (was - sale) * 10000 // was if was is not None else None
    cheaper = best is not None and best < sale

    def res(verdict: Verdict, reason: str) -> DiscountCheckResult:
        return DiscountCheckResult(verdict, reason, ref, claimed_bp, real_bp, n, cheaper)

    if was is None or was == sale:
        return res(Verdict.NO_DISCOUNT_CLAIMED, "no discount claimed")
    if ref is None or real_bp is None or claimed_bp is None:
        reason = f"only {n} pre-sale price points (need {MIN_HISTORY_POINTS})"
        return res(Verdict.INSUFFICIENT_HISTORY, reason)
    if sale >= ref:
        return res(Verdict.INFLATED, f"sale price is not below the 30-day market low of {ref}")
    if claimed_bp - real_bp > TOLERANCE_BP:
        return res(Verdict.INFLATED, f"claimed {claimed_bp} bp, real {real_bp} bp vs 30-day market low")
    if cheaper:
        return res(Verdict.NOT_BEST_PRICE, f"real discount, but another shop sells it for {best}")
    return res(Verdict.GENUINE, f"real discount of {real_bp} bp vs 30-day market low")
