# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_discount_check.py
# Pathname:  tests/test_discount_check.py
# Purpose:   One test per row DC-01..DC-19 of the test table in doc/design/discount_check.md
from family_shopper.discount_check import PricePoint, Verdict, check_discount


def H(a: int, b: int, price: int, override: dict[int, int] | None = None) -> list[PricePoint]:
    """One point per day a..b at price cents; override maps days_ago -> price."""
    override = override or {}
    return [PricePoint(d, override.get(d, price)) for d in range(a, b + 1)]


def _check(was, sale, history, sale_days, best, verdict, ref, claimed, real, n, cheaper):
    r = check_discount(sale, was, history, sale_days, best)
    assert r.verdict is Verdict(verdict)
    assert r.reference_low_cents == ref
    assert r.claimed_discount_bp == claimed
    assert r.real_discount_bp == real
    assert r.history_points_used == n
    assert r.cheaper_elsewhere is cheaper
    return r


def test_dc_01_genuine():
    _check(10000, 8000, H(1,30,10000), 0, None, "GENUINE", 10000, 2000, 2000, 30, False)

def test_dc_02_inflated_was_price():
    _check(15000, 9900, H(1,30,10000), 0, None, "INFLATED", 10000, 3400, 100, 30, False)

def test_dc_03_sale_not_below_low():
    _check(12000, 10000, H(1,30,10000), 0, None, "INFLATED", 10000, 1666, 0, 30, False)

def test_dc_04_cheaper_elsewhere():
    _check(10000, 8000, H(1,30,10000), 0, 7500, "NOT_BEST_PRICE", 10000, 2000, 2000, 30, True)

def test_dc_05_equal_best_offer():
    _check(10000, 8000, H(1,30,10000), 0, 8000, "GENUINE", 10000, 2000, 2000, 30, False)

def test_dc_06_no_was_price():
    _check(None, 8000, H(1,30,10000), 0, None, "NO_DISCOUNT_CLAIMED", 10000, None, 2000, 30, False)

def test_dc_07_was_equals_sale():
    _check(8000, 8000, H(1,30,10000), 0, None, "NO_DISCOUNT_CLAIMED", 10000, 0, 2000, 30, False)

def test_dc_08_was_below_sale():
    _check(7000, 8000, H(1,30,10000), 0, None, "INVALID_INPUT", None, None, None, 0, False)

def test_dc_09_zero_sale():
    _check(10000, 0, H(1,30,10000), 0, None, "INVALID_INPUT", None, None, None, 0, False)

def test_dc_10_zero_history_price():
    _check(10000, 8000, [PricePoint(1, 0)], 0, None, "INVALID_INPUT", None, None, None, 0, False)

def test_dc_11_empty_history():
    _check(10000, 8000, [], 0, None, "INSUFFICIENT_HISTORY", None, 2000, None, 0, False)

def test_dc_12_six_points():
    _check(10000, 8000, H(1,6,10000), 0, None, "INSUFFICIENT_HISTORY", None, 2000, None, 6, False)

def test_dc_13_seven_points():
    _check(10000, 8000, H(1,7,10000), 0, None, "GENUINE", 10000, 2000, 2000, 7, False)

def test_dc_14_sale_days_excluded():
    _check(10000, 8000, H(0,3,8000) + H(4,30,10000), 3, None, "GENUINE", 10000, 2000, 2000, 27, False)

def test_dc_15_tolerance_edge_ok():
    _check(10127, 8000, H(1,30,10000), 0, None, "GENUINE", 10000, 2100, 2000, 30, False)

def test_dc_16_tolerance_edge_over():
    _check(10128, 8000, H(1,30,10000), 0, None, "INFLATED", 10000, 2101, 2000, 30, False)

def test_dc_17_dip_in_window():
    _check(10000, 8000, H(1,30,10000, {10: 8500}), 0, None, "INFLATED", 8500, 2000, 588, 30, False)

def test_dc_18_ignores_old_points():
    _check(10000, 8000, H(1,30,10000) + H(31,60,5000), 0, 7999, "NOT_BEST_PRICE", 10000, 2000, 2000, 30, True)

def test_dc_19_inflated_and_cheaper():
    _check(15000, 9900, H(1,30,10000), 0, 9000, "INFLATED", 10000, 3400, 100, 30, True)
