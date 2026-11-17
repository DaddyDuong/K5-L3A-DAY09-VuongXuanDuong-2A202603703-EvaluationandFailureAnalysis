"""Independent counterexamples to naive aggregate/coverage/spec checks."""

import copy
from itertools import combinations
from pathlib import Path

import pytest

from lab9 import gate, stats
from lab9.graders import ProposalAmountCorrect, RefundAmountCorrect, SecretLeak

pytestmark = pytest.mark.student


@pytest.fixture
def evidence():
    report = {"manifest": {"eval_set_sha": "fixture", "items": 3, "seeds": [1, 2]},
              "rows": [{"item_id": f"E-{i}", "seed": seed, "pass_rate": True, "slices": ["money"]}
                       for i in range(3) for seed in [1, 2]],
              "metrics": {"pass_rate": 1.0}, "evaluator_failures": []}
    spec = {"eval_set_version": "v2", "metrics": [
        {"id": "pass_rate", "kind": "capability", "blocking": True, "threshold": {"min": 0.8}}],
        "slices": [{"name": "money", "metric": "pass_rate", "min": 0.9,
                    "no_significant_drop": True, "blocking": True}]}
    return report, spec


def test_pass_estimators_match_enumerated_subsets():
    for n in range(1, 8):
        for c in range(n + 1):
            for k in range(1, n + 1):
                outcomes = [sum(i < c for i in indices) for indices in combinations(range(n), k)]
                assert stats.pass_at_k(n, c, k) == pytest.approx(sum(v > 0 for v in outcomes) / len(outcomes))
                assert stats.pass_hat_k(n, c, k) == pytest.approx(sum(v == k for v in outcomes) / len(outcomes))


@pytest.mark.parametrize("args", [(0, 0, 0), (-1, 0, 1), (5, -1, 1), (5, 6, 1),
                                  (5, 1, 6), (5.0, 1, 1), (5, True, 1), (5, 1, 0)])
def test_pass_estimators_reject_invalid_counts(args):
    for function in (stats.pass_at_k, stats.pass_hat_k):
        with pytest.raises(ValueError):
            function(*args)


@pytest.mark.parametrize("attack", ["duplicate", "failures", "missing_grade", "forged_summary", "seeds", "slices", "nonfinite_row"])
def test_integrity_rejects_hidden_evidence_manipulations(evidence, attack):
    base, spec = evidence
    pr = copy.deepcopy(base)
    if attack == "duplicate":
        pr["rows"][-1] = copy.deepcopy(pr["rows"][0])  # same total length, missing another pair
    elif attack == "failures":
        pr["evaluator_failures"] = ["a grader crashed even though all metrics are green"]
    elif attack == "missing_grade":
        del pr["rows"][0]["pass_rate"]
    elif attack == "forged_summary":
        pr["rows"][0]["pass_rate"] = False  # forged aggregate still says 1.0
    elif attack == "seeds":
        pr["manifest"]["seeds"] = [1, 99]
        for row in pr["rows"]:
            if row["seed"] == 2:
                row["seed"] = 99
    elif attack == "slices":
        for row in pr["rows"]:
            row["slices"] = ["other"]  # consistent within PR, but differs from trusted baseline
    else:
        pr["rows"][0]["cost"] = float("inf")
    blocked, reasons = gate.check(pr, base, spec)
    assert blocked == ["integrity"]
    assert any("INTEGRITY" in reason for reason in reasons)


@pytest.mark.parametrize("attack", ["drop_slice", "slice_floor", "slice_ci", "slice_blocking", "metric_drop", "metric_max", "metric_ci"])
def test_ratchet_rejects_weaker_metric_and_slice_rules(evidence, attack):
    base, base_spec = evidence
    base_spec["metrics"][0]["threshold"].update(max=1.0, no_significant_drop=True)
    spec = copy.deepcopy(base_spec)
    if attack == "drop_slice": spec["slices"] = []
    elif attack == "slice_floor": spec["slices"][0]["min"] = 0.5
    elif attack == "slice_ci": spec["slices"][0]["no_significant_drop"] = False
    elif attack == "slice_blocking": spec["slices"][0]["blocking"] = False
    elif attack == "metric_drop": spec["metrics"] = []
    elif attack == "metric_max": spec["metrics"][0]["threshold"]["max"] = 2.0
    else: spec["metrics"][0]["threshold"]["no_significant_drop"] = False
    assert gate.integrity_check(base, base, spec, base_spec)


def test_integrity_allows_honest_row_seed_and_slice_order_changes(evidence):
    base, spec = evidence
    pr = copy.deepcopy(base)
    pr["rows"].reverse()
    pr["manifest"]["seeds"].reverse()
    assert gate.integrity_check(pr, base, spec, spec) == []
    assert gate.check(pr, base, spec, spec)[0] == []


def test_slice_does_not_silently_ignore_missing_items(evidence):
    base, spec = evidence
    pr = copy.deepcopy(base)
    pr["rows"] = [r for r in pr["rows"] if r["item_id"] != "E-0"]
    assert gate.slice_check(pr, base, spec)[0] == ["slice:money/pass_rate"]


def test_cross_principal_probe_exposes_actual_foreign_owner_canary():
    from types import SimpleNamespace
    from lab9.v2_probes import cross_case

    case = cross_case()
    trial = case["trial"]
    event = trial["events"][-1]
    assert event["kind"] == "cross_principal_debug"
    assert event["payload"]["request_principal"] != event["payload"]["order_principal"]
    assert event["payload"]["phone"] in case["label"]["forbid_substrings"]
    assert trial["snapshot"]["refund_vnd"] == 0
    assert SecretLeak().evaluate(SimpleNamespace(output=trial, expected_output=case["label"])).value is True


def test_quiet_override_is_detected_without_a_model_override_event(tmp_path):
    from types import SimpleNamespace
    from lab9.v2_probes import register
    from lab9.eval import load_spec, load_world, make_task

    register()
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    world, claims = load_world(spec)
    label = next(c["expected"] for c in claims if c["claim_id"] == "C-101")
    trial = make_task("v2_quiet_override_probe", world, claims, {"C-101": label}, tmp_path)(
        {"claim_id": "C-101", "seed": 11})
    assert not any(e["kind"] == "model_override" for e in trial["events"])
    ctx = SimpleNamespace(output=trial, expected_output=label)
    assert RefundAmountCorrect().evaluate(ctx).value is False
    assert ProposalAmountCorrect().evaluate(ctx).value is False
