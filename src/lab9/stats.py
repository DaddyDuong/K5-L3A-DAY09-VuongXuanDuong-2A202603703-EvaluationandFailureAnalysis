"""Statistics students implement (M2 judge calibration, M4 paired bootstrap).

Rules: a judge is a classifier -- measure it like one. A higher mean is not
"better" until the paired CI of the difference excludes 0.
Reference values to self-check are in tests/test_lab9_stats.py.
"""

from __future__ import annotations

from collections.abc import Sequence
import math

POS = "FAIL"   # the judge's job is to FIND failures, so FAIL is the positive class


def confusion(human: Sequence[str], judge: Sequence[str]) -> dict[str, int]:
    """tp/fp/fn/tn with FAIL as positive."""
    if len(human) != len(judge):
        raise ValueError("human and judge must contain the same number of labels")
    counts = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for expected, predicted in zip(human, judge):
        if expected not in ("PASS", POS) or predicted not in ("PASS", POS):
            raise ValueError("labels must be PASS or FAIL")
        if predicted == POS:
            counts["tp" if expected == POS else "fp"] += 1
        else:
            counts["fn" if expected == POS else "tn"] += 1
    return counts


def precision_recall(human: Sequence[str], judge: Sequence[str]) -> tuple[float, float]:
    cm = confusion(human, judge)
    predicted_failures = cm["tp"] + cm["fp"]
    actual_failures = cm["tp"] + cm["fn"]
    return (cm["tp"] / predicted_failures if predicted_failures else 0.0,
            cm["tp"] / actual_failures if actual_failures else 0.0)


def cohen_kappa(human: Sequence[str], judge: Sequence[str]) -> float:
    """kappa = (p_o - p_e) / (1 - p_e). Raise ValueError when undefined (p_e == 1):
    a constant judge has no signal and must FAIL calibration, not pass on a technicality."""
    cm = confusion(human, judge)
    n = len(human)
    if not n:
        raise ValueError("kappa is undefined for empty labels")
    human_fail = cm["tp"] + cm["fn"]
    judge_fail = cm["tp"] + cm["fp"]
    # Multiply p_o and p_e by n**2 to keep the undefined-case check exact.
    expected = human_fail * judge_fail + (n - human_fail) * (n - judge_fail)
    denominator = n * n - expected
    if denominator == 0:
        raise ValueError("kappa is undefined when expected agreement equals one")
    return (n * (cm["tp"] + cm["tn"]) - expected) / denominator


def rogan_gladen(observed_rate: float, sensitivity: float, specificity: float) -> float:
    """Correct an observed failure rate for judge error; clip to [0, 1]."""
    if any(not math.isfinite(value) or not 0.0 <= value <= 1.0
           for value in (observed_rate, sensitivity, specificity)):
        raise ValueError("rates must be finite probabilities between zero and one")
    denominator = sensitivity + specificity - 1.0
    if denominator == 0.0:
        raise ValueError("Rogan-Gladen is undefined when sensitivity + specificity equals one")
    corrected = (observed_rate + specificity - 1.0) / denominator
    return min(1.0, max(0.0, corrected))


def paired_bootstrap(a: Sequence[float], b: Sequence[float], *, n_resamples: int = 1000,
                     rng: int = 2027, confidence: float = 0.95) -> tuple[float, float, float]:
    """a[i], b[i] = per-item mean over seeds, SAME items, SAME order.
    Return (mean(a)-mean(b), lo, hi) with scipy.stats.bootstrap(paired=True, method="percentile",
    rng=numpy.random.default_rng(rng)). If a == b everywhere return (0.0, 0.0, 0.0)."""
    import numpy as np
    from scipy.stats import bootstrap

    first, second = np.asarray(a, dtype=float), np.asarray(b, dtype=float)
    if first.ndim != 1 or second.ndim != 1 or first.shape != second.shape or not first.size:
        raise ValueError("paired samples must be non-empty one-dimensional arrays of equal length")
    if not np.isfinite(first).all() or not np.isfinite(second).all():
        raise ValueError("paired samples must contain only finite values")
    if isinstance(n_resamples, bool) or not isinstance(n_resamples, (int, np.integer)) or n_resamples < 1:
        raise ValueError("n_resamples must be a positive integer")
    if not math.isfinite(confidence) or not 0.0 < confidence < 1.0:
        raise ValueError("confidence must be strictly between zero and one")
    if np.array_equal(first, second):
        return 0.0, 0.0, 0.0
    delta = float(first.mean() - second.mean())
    if first.size == 1:
        return delta, delta, delta  # the empirical resampling distribution has one outcome

    def mean_difference(x, y, axis):
        return np.mean(x, axis=axis) - np.mean(y, axis=axis)

    result = bootstrap((first, second), mean_difference, paired=True, vectorized=True,
                       n_resamples=n_resamples, method="percentile", confidence_level=confidence,
                       rng=np.random.default_rng(rng))
    return delta, float(result.confidence_interval.low), float(result.confidence_interval.high)


def pass_at_k(n: int, c: int, k: int) -> float:
    """Probability that AT LEAST ONE of k trials drawn from n (c of them passing) passes.
    Unbiased estimator (Chen et al. 2021): 1 - C(n-c, k) / C(n, k). Raise ValueError if k > n."""
    _validate_pass_counts(n, c, k)
    return 1.0 if n - c < k else 1.0 - math.comb(n - c, k) / math.comb(n, k)


def pass_hat_k(n: int, c: int, k: int) -> float:
    """pass^k (tau-bench, Yao et al. 2024): probability that ALL k trials drawn from n pass.
    Unbiased estimator: C(c, k) / C(n, k). Raise ValueError if k > n.
    pass^k <= pass@1 <= pass@k; a reliable agent keeps pass^k close to pass@1."""
    _validate_pass_counts(n, c, k)
    return 0.0 if c < k else math.comb(c, k) / math.comb(n, k)


def _validate_pass_counts(n: int, c: int, k: int) -> None:
    from numbers import Integral

    if any(isinstance(value, bool) or not isinstance(value, Integral) for value in (n, c, k)):
        raise ValueError("n, c and k must be integers")
    if n < 1 or not 0 <= c <= n or not 1 <= k <= n:
        raise ValueError("require n >= 1, 0 <= c <= n and 1 <= k <= n")
