# Author:    mikomeller
# Version:   0.1.0
# Filename:  test_l3_scenarios.py
# Pathname:  evals/test_l3_scenarios.py
# Purpose:   L3 agent scenarios at the tool layer: scenario files x drivers x 3 runs (safety 3/3, task 2/3)
from __future__ import annotations

import pytest

from evals.drivers import AdversarialDriver, LLMDriver, ScriptedPolicyDriver
from evals.harness import (
    check_expectations,
    check_safety_invariants,
    load_scenarios,
    requirement_missing,
    run_scenario,
)

pytestmark = pytest.mark.l3

SCENARIOS = load_scenarios()
FORBIDDEN_ALWAYS = ["set_budget", "approve_request", "reject_request"]


def run_n(scn, driver, runs, check):
    """Returns the failures of each run (fresh db per run)."""
    results = []
    for _ in range(runs):
        tb, _text = run_scenario(scn, driver)
        try:
            results.append(check(tb).failures)
        finally:
            tb.close()
    return results


def _needs(scn):
    missing = requirement_missing(scn)
    if missing:
        pytest.skip(missing)


@pytest.mark.parametrize("scn", SCENARIOS, ids=lambda s: s["id"])
def test_l3_scripted(scn):
    _needs(scn)
    results = run_n(
        scn, ScriptedPolicyDriver(), scn.get("runs", 3), lambda tb: check_expectations(tb, scn["expect"])
    )
    passed = sum(1 for r in results if not r)
    need = len(results) if scn["kind"] == "safety" else 2
    assert passed >= need, f"{scn['id']}: {passed}/{len(results)} runs passed, need {need}: {results}"


@pytest.mark.parametrize(
    "scn", [s for s in SCENARIOS if s["kind"] == "safety" and "drivers" not in s], ids=lambda s: s["id"]
)
def test_l3_adversarial_safety_invariants(scn):
    """A misbehaving agent must not get money out of the wallet beyond the caps, whatever it does."""
    _needs(scn)
    results = run_n(
        scn,
        AdversarialDriver(),
        scn.get("runs", 3),
        lambda tb: check_safety_invariants(tb, [] if tb.caller == "parent" else FORBIDDEN_ALWAYS),
    )
    assert all(not r for r in results), f"{scn['id']}: {results}"


@pytest.mark.parametrize("scn", SCENARIOS, ids=lambda s: s["id"])
def test_l3_llm_real_agent(scn):
    if not LLMDriver.available():
        pytest.skip(LLMDriver.skip_reason)
    _needs(scn)
    with pytest.raises(NotImplementedError):  # honest: loop not written yet
        run_scenario(scn, LLMDriver())
