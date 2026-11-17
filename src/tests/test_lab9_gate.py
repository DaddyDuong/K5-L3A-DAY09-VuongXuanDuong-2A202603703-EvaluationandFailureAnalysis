"""M4: pairing, input validation, and release decisions from generated reports."""

import json
from pathlib import Path

import pytest

from lab9 import gate, stats
from lab9.eval import load_spec, per_item

pytestmark = pytest.mark.student


def test_lab9_bootstrap_keeps_correlated_items_paired():
    delta, low, high = stats.paired_bootstrap([101, 102, 103, 104], [100, 101, 102, 103])
    assert (delta, low, high) == (1.0, 1.0, 1.0)


def test_lab9_bootstrap_is_reproducible_and_reverses_the_difference():
    a, b = [1.0, 0.2, 0.8, 0.0], [0.2, 0.8, 0.4, 0.0]
    delta, low, high = stats.paired_bootstrap(a, b)
    assert stats.paired_bootstrap(a, b) == (delta, low, high)
    assert stats.paired_bootstrap(b, a) == pytest.approx((-delta, -high, -low))


@pytest.mark.parametrize("a,b,kwargs", [
    ([], [], {}),
    ([1], [1, 0], {}),
    ([[1, 0]], [[1, 0]], {}),
    ([float("nan"), 1], [0, 1], {}),
    ([0, 1], [0, float("inf")], {}),
    ([1, 0], [0, 1], {"n_resamples": 0}),
    ([1, 0], [0, 1], {"confidence": 1.0}),
])
def test_lab9_bootstrap_rejects_invalid_pairs(a, b, kwargs):
    with pytest.raises(ValueError):
        stats.paired_bootstrap(a, b, **kwargs)


@pytest.fixture(scope="module")
def core_reports():
    def read(name):
        return json.loads(Path(f"reports/{name}.json").read_text(encoding="utf-8"))
    return load_spec(), read("baseline_v1"), read("eval_fixed"), read("eval_seeded_regression")


def test_lab9_gate_accepts_baseline_itself_and_fixed(core_reports):
    spec, base, fixed, _ = core_reports
    assert base["shape"] == "swarm"
    assert gate.check(base, base, spec)[0] == []
    assert gate.check(fixed, base, spec)[0] == []


def test_lab9_gate_blocks_seeded_regression_with_reference_ci(core_reports):
    spec, base, _, bad = core_reports
    blocked, _ = gate.check(bad, base, spec)
    assert "pass_rate" in blocked
    current, baseline = per_item(bad, "pass_rate"), per_item(base, "pass_rate")
    keys = sorted(baseline)
    delta, low, high = stats.paired_bootstrap([current[k] for k in keys], [baseline[k] for k in keys])
    assert delta == pytest.approx(-0.271, abs=0.01)
    assert low == pytest.approx(-0.500, abs=0.01)
    assert high == pytest.approx(-0.057, abs=0.01)


def test_lab9_gate_uses_the_confidence_level_in_the_spec(core_reports, monkeypatch):
    spec, base, fixed, _ = core_reports
    spec = {**spec, "bootstrap": {**spec["bootstrap"], "confidence": 0.9}}
    levels = []

    def record_confidence(a, b, **kwargs):
        levels.append(kwargs["confidence"])
        return 0.0, 0.0, 0.0

    monkeypatch.setattr(stats, "paired_bootstrap", record_confidence)
    gate.check(fixed, base, spec)
    assert levels and set(levels) == {0.9}
