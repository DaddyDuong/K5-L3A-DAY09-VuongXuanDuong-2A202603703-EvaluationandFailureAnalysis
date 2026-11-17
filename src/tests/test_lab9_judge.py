"""M2 calibration decisions and undefined/near-threshold cases."""

import csv
import math
from pathlib import Path

import pytest

from lab9 import stats
from lab9.judge import calibrate

pytestmark = pytest.mark.student


def write_labels(path, human, judge):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["item_id", "reply", "human", "judge"])
        writer.writerows((str(i), "reply", h, j) for i, (h, j) in enumerate(zip(human, judge)))


@pytest.mark.parametrize("name,passed,confusion", [
    ("tone", True, {"tp": 24, "fp": 4, "fn": 6, "tn": 66}),
    ("helpful", False, {"tp": 9, "fp": 0, "fn": 21, "tn": 70}),
])
def test_lab9_calibration_accepts_tone_and_rejects_helpful(name, passed, confusion):
    result = calibrate(Path(f"data/eval/judge_{name}_public.csv"))
    assert result["passed"] is passed
    assert result["confusion"] == confusion
    assert result["corrected_fail_rate"] == pytest.approx(0.3)


def test_lab9_constant_judge_fails_calibration_without_crashing(tmp_path):
    path = tmp_path / "constant.csv"
    write_labels(path, ["PASS"] * 5, ["PASS"] * 5)
    result = calibrate(path)
    assert result["passed"] is False
    assert math.isnan(result["kappa"])
    assert math.isnan(result["corrected_fail_rate"])


def test_lab9_display_rounding_cannot_pass_a_below_floor_judge(tmp_path):
    # Precision 0.7998 displays as 0.8 but must fail the actual 0.8 floor.
    path = tmp_path / "near_floor.csv"
    human = ["FAIL"] * 3999 + ["PASS"] * 6001
    judge = ["FAIL"] * 5000 + ["PASS"] * 5000
    write_labels(path, human, judge)
    result = calibrate(path)
    assert result["precision"] == 0.8
    assert result["recall"] == 1.0
    assert result["kappa"] >= 0.6
    assert result["passed"] is False


@pytest.mark.parametrize("human,judge", [
    (["PASS"], []),
    (["UNKNOWN"], ["PASS"]),
    (["FAIL"], ["UNKNOWN"]),
])
def test_lab9_confusion_rejects_unpaired_or_invalid_labels(human, judge):
    with pytest.raises(ValueError):
        stats.confusion(human, judge)


def test_lab9_zero_denominators_and_no_agreement_signal():
    assert stats.precision_recall([], []) == (0.0, 0.0)
    assert stats.precision_recall(["PASS"], ["PASS"]) == (0.0, 0.0)
    assert stats.cohen_kappa(["FAIL", "PASS"], ["PASS", "PASS"]) == 0.0
    assert stats.cohen_kappa(["FAIL", "PASS"], ["PASS", "FAIL"]) == -1.0
    with pytest.raises(ValueError):
        stats.cohen_kappa([], [])


def test_lab9_rogan_gladen_rejects_unidentifiable_or_invalid_rates():
    assert stats.rogan_gladen(1.0, 0.8, 0.9) == 1.0
    with pytest.raises(ValueError):
        stats.rogan_gladen(0.5, 0.5, 0.5)
    with pytest.raises(ValueError):
        stats.rogan_gladen(float("nan"), 0.8, 0.9)
    with pytest.raises(ValueError):
        stats.rogan_gladen(1.1, 0.8, 0.9)
