<!--
Author:    mikomeller
Version:   0.1.0
Filename:  discount_check.md
Pathname:  doc/design/discount_check.md
Purpose:   Design of the deterministic "is this discount real?" checker (ticket #25) and its MCP tool check_discount
-->
# Discount check (`check_discount`)

**Purpose.** Tell a family member whether an advertised discount is real, measured against the lowest price of the
30 days before the sale, and whether another shop sells it cheaper now. Serves eval **S-09** ("Is now a good time to
buy X?", no order) and is called before `place_order` whenever a product is advertised as discounted.
Diagram: `doc/diagrams/discount_check.mmd`.

## Assessment of ticket #25 — verdict: idea good, design needs changes
| # | Ticket claim | Assessment |
|---|---|---|
| 1 | Honesty rule `claimed_discount >= (list − low_30)/list` | **Wrong.** With list = "was": `(was−sale)/was >= (was−low)/was` ⇔ `sale <= low`. It only checks that the sale price is at/below the 30-day low and never checks whether the "was" price is inflated. Example DC-02: was 150.00, low 100.00, sale 99.00 → ticket says honest (34% ≥ 33%), real discount is 1%. Correct test: claimed discount must not exceed the discount vs the 30-day low (⇔ was ≤ low), plus tolerance. |
| 2 | Reference = "30-day low" | Incomplete. Rule we apply: lowest price in the 30 days **before the reduction** (EU Price Indication Directive Art. 6a, Omnibus — legal detail unverified). Sale days must be excluded, else the sale price lowers its own reference (DC-14). |
| 3 | "30/90-day low" | **Not available.** idealo `get_product_price_history` returns 30 days only. If the sale started N days ago, only 30−N pre-sale days are visible. |
| 4 | "Category graph" for substitutes | **Does not exist** in the idealo MCP (4 tools only). Substitutes = out of scope; agent may call `search_products` separately. |
| 5 | Node/TypeScript orchestrator, web app | Rejected: project is Python 3.12, agent + MCP; no web app. |
| 6 | Deterministic, testable scorer | **Sound** — kept. Integer cents and basis points, no floats, no LLM. |
| 7 | Live offers decide "not best price" | Sound, if compared on total price incl. shipping. |
| 8 | Empty/short history, was < sale, zero prices, rounding, tolerance | Not addressed — defined below. |
| 9 | idealo history = retailer's own price history | **Unverified / probably not:** idealo history is likely the cross-shop daily lowest price, a proxy that is stricter than the legal per-retailer reference. Reason text says "market low". |

## Function (`src/family_shopper/discount_check.py`, pure, no I/O)
```python
TOLERANCE_BP = 100        # 1.00 percentage point
MIN_HISTORY_POINTS = 7
WINDOW_DAYS = 30

class Verdict(str, Enum):
    GENUINE = "GENUINE"; INFLATED = "INFLATED"; NOT_BEST_PRICE = "NOT_BEST_PRICE"
    NO_DISCOUNT_CLAIMED = "NO_DISCOUNT_CLAIMED"; INSUFFICIENT_HISTORY = "INSUFFICIENT_HISTORY"
    INVALID_INPUT = "INVALID_INPUT"

@dataclass(frozen=True)
class PricePoint:
    days_ago: int        # 0 = today, 1 = yesterday, ...
    price_cents: int     # idealo daily lowest total price

@dataclass(frozen=True)
class DiscountCheckResult:
    verdict: Verdict
    reason: str
    reference_low_cents: int | None   # min of window; None if window < MIN_HISTORY_POINTS or invalid
    claimed_discount_bp: int | None   # None if no "was" price or invalid
    real_discount_bp: int | None      # vs reference_low, clamped at 0; None if no reference
    history_points_used: int          # len(window); 0 if invalid
    cheaper_elsewhere: bool           # best_offer_cents < sale_price_cents; False if invalid/None

def check_discount(sale_price_cents: int, claimed_was_cents: int | None,
                   history: list[PricePoint], sale_days: int = 0,
                   best_offer_cents: int | None = None) -> DiscountCheckResult: ...
```
`sale_days` = number of days the sale has already run before today (0 = started today). Duplicate `days_ago` allowed.

## Algorithm (integers only, `//` = floor division)
1. **Validate** → `INVALID_INPUT` if: `sale_price_cents <= 0`; `claimed_was_cents` given and `<= 0` or `< sale_price_cents`;
   `sale_days < 0`; any point with `days_ago < 0` or `price_cents <= 0`; `best_offer_cents` given and `<= 0`.
   Reason: `"invalid input: <first failing rule>"`. All computed fields None/0/False.
2. `window = [p.price_cents for p in history if sale_days < p.days_ago <= 30]`; `n = len(window)`.
3. If `n >= 7`: `ref = min(window)`, `real_bp = max(0, (ref − sale) * 10000 // ref)`; else `ref = real_bp = None`.
4. `claimed_bp = (was − sale) * 10000 // was` if was given, else None. `cheaper = best is not None and best < sale`.
5. If was is None or was == sale → `NO_DISCOUNT_CLAIMED`, reason `"no discount claimed"`.
6. If `n < 7` → `INSUFFICIENT_HISTORY`, reason `"only <n> pre-sale price points (need 7)"`.
7. If `sale >= ref` → `INFLATED`, reason `"sale price is not below the 30-day market low of <ref>"`.
8. If `claimed_bp − real_bp > TOLERANCE_BP` → `INFLATED`, reason `"claimed <claimed_bp> bp, real <real_bp> bp vs 30-day market low"`.
9. If `cheaper` → `NOT_BEST_PRICE`, reason `"real discount, but another shop sells it for <best>"`.
10. Else `GENUINE`, reason `"real discount of <real_bp> bp vs 30-day market low"`.

`cheaper_elsewhere` is set in steps 5–10, so an INFLATED result still tells the agent a cheaper offer exists.
Equal best offer (`best == sale`) is not cheaper.

## MCP tool `check_discount` (deal-tools server, read-only, all roles)
Input: `{"sale_price_cents": int, "claimed_was_cents": int|null, "history": [{"days_ago": int, "price_cents": int}],
"sale_days": int = 0, "best_offer_cents": int|null}`. Output: the result fields as JSON, `verdict` as string.
The agent fills `history` from `get_product_price_history` (dates → `days_ago`) and `best_offer_cents` = cheapest
total (price + shipping) from `get_product_offers`. Never places an order; never errors — bad input → `INVALID_INPUT`.

## Test cases (H(a..b)=p: one point per day a..b at p cents; defaults sale_days=0, best=None)
| ID | was | sale | history | sale_days / best | verdict | ref | claimed_bp | real_bp | n | cheaper |
|---|---|---|---|---|---|---|---|---|---|---|
| DC-01 | 10000 | 8000 | H(1..30)=10000 | 0 / None | GENUINE | 10000 | 2000 | 2000 | 30 | F |
| DC-02 | 15000 | 9900 | H(1..30)=10000 | 0 / None | INFLATED | 10000 | 3400 | 100 | 30 | F |
| DC-03 | 12000 | 10000 | H(1..30)=10000 | 0 / None | INFLATED (step 7) | 10000 | 1666 | 0 | 30 | F |
| DC-04 | 10000 | 8000 | H(1..30)=10000 | 0 / 7500 | NOT_BEST_PRICE | 10000 | 2000 | 2000 | 30 | T |
| DC-05 | 10000 | 8000 | H(1..30)=10000 | 0 / 8000 | GENUINE | 10000 | 2000 | 2000 | 30 | F |
| DC-06 | None | 8000 | H(1..30)=10000 | 0 / None | NO_DISCOUNT_CLAIMED | 10000 | None | 2000 | 30 | F |
| DC-07 | 8000 | 8000 | H(1..30)=10000 | 0 / None | NO_DISCOUNT_CLAIMED | 10000 | 0 | 2000 | 30 | F |
| DC-08 | 7000 | 8000 | H(1..30)=10000 | 0 / None | INVALID_INPUT | None | None | None | 0 | F |
| DC-09 | 10000 | 0 | H(1..30)=10000 | 0 / None | INVALID_INPUT | None | None | None | 0 | F |
| DC-10 | 10000 | 8000 | [(1, 0)] | 0 / None | INVALID_INPUT | None | None | None | 0 | F |
| DC-11 | 10000 | 8000 | [] | 0 / None | INSUFFICIENT_HISTORY | None | 2000 | None | 0 | F |
| DC-12 | 10000 | 8000 | H(1..6)=10000 | 0 / None | INSUFFICIENT_HISTORY | None | 2000 | None | 6 | F |
| DC-13 | 10000 | 8000 | H(1..7)=10000 | 0 / None | GENUINE | 10000 | 2000 | 2000 | 7 | F |
| DC-14 | 10000 | 8000 | H(0..3)=8000 + H(4..30)=10000 | 3 / None | GENUINE | 10000 | 2000 | 2000 | 27 | F |
| DC-15 | 10127 | 8000 | H(1..30)=10000 | 0 / None | GENUINE (diff 100) | 10000 | 2100 | 2000 | 30 | F |
| DC-16 | 10128 | 8000 | H(1..30)=10000 | 0 / None | INFLATED (diff 101) | 10000 | 2101 | 2000 | 30 | F |
| DC-17 | 10000 | 8000 | H(1..30)=10000 but day 10 = 8500 | 0 / None | INFLATED | 8500 | 2000 | 588 | 30 | F |
| DC-18 | 10000 | 8000 | H(1..30)=10000 + H(31..60)=5000 | 0 / 7999 | NOT_BEST_PRICE | 10000 | 2000 | 2000 | 30 | T |
| DC-19 | 15000 | 9900 | H(1..30)=10000 | 0 / 9000 | INFLATED | 10000 | 3400 | 100 | 30 | T |

Checks: 5100·10000//15000=3400 · 2000·10000//12000=1666 · 2127·10000//10127=2100 · 2128·10000//10128=2101 · 500·10000//8500=588.
DC-02 is the ticket formula's false "honest"; DC-14 fails if sale days are not excluded; DC-18 ignores points > 30 days.

## Decisions
- Inflation test `claimed_bp − real_bp > 100 bp`; rejected: ticket formula (checks only sale ≤ low, see #1).
- Exclude the sale days via `sale_days`; rejected: whole 30-day window (sale price would be its own reference).
- One verdict + `cheaper_elsewhere` flag; rejected: multi-label verdict list (harder to test and to phrase).
- Insufficient history below 7 points → no verdict; rejected: judging on 1–2 points (one outlier decides).
- Floor division for bp; rejected: floats/rounding half-up (non-deterministic edge cases).

## Open questions
1. Does `get_product_price_history` return the cross-shop daily low or per-shop prices, and as dates or offsets? (unverified)
2. How does the agent learn `sale_days`? Default 0 may make a long-running sale look INSUFFICIENT/INFLATED wrongly.
3. Is 1 percentage point the right tolerance, and 7 points the right minimum?
4. Should INFLATED block `place_order` or only warn? Proposal: warn, the user decides.
