"""Validate evaluation evidence and prevent weaker policies on the same eval set."""

from __future__ import annotations

from collections import defaultdict
import math
from numbers import Real

from lab9 import stats
from lab9.graders import GRADERS


def finite(value) -> bool:
    try:
        return isinstance(value, Real) and math.isfinite(value)
    except OverflowError:
        return False


def validate_report(report: dict, spec: dict, name: str) -> tuple[list[str], dict]:
    errors, pairs = [], {}
    if not isinstance(report, dict):
        return [f"{name}: report must be an object"], pairs
    manifest, rows, metrics = (report.get(k) for k in ("manifest", "rows", "metrics"))
    if not isinstance(manifest, dict) or not isinstance(rows, list) or not isinstance(metrics, dict):
        return [f"{name}: missing manifest, rows or metrics"], pairs
    count, seeds = manifest.get("items"), manifest.get("seeds")
    if not isinstance(manifest.get("eval_set_sha"), str) or not manifest["eval_set_sha"]:
        errors.append(f"{name}: missing eval-set SHA")
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        return [f"{name}: invalid manifest item count"], pairs
    if (not isinstance(seeds, list) or not seeds
            or any(isinstance(s, bool) or not isinstance(s, int) for s in seeds)
            or len(set(seeds)) != len(seeds)):
        return [f"{name}: seeds must be a non-empty set of integer identifiers"], pairs
    if "seeds" in spec and set(seeds) != set(spec["seeds"]):
        errors.append(f"{name}: manifest seeds differ from the metric spec")
    if len(rows) != count * len(seeds):
        errors.append(f"{name}: row count {len(rows)} != {count} items x {len(seeds)} seeds")
    failures = report.get("evaluator_failures")
    if not isinstance(failures, list) or failures:
        errors.append(f"{name}: evaluator_failures must be an empty list")
    definitions = spec.get("metrics")
    if (not isinstance(definitions, list) or not definitions
            or any(not isinstance(m, dict) or not isinstance(m.get("id"), str) for m in definitions)):
        return errors + ["metric spec has no metrics"], pairs
    metric_ids = [m["id"] for m in definitions]
    if len(set(metric_ids)) != len(metric_ids):
        errors.append("duplicate metric definitions")
    graded = {mid for mid in metric_ids if mid in GRADERS
              or any(isinstance(r, dict) and mid in r for r in rows)}
    for mid, value in metrics.items():
        if value is None and mid == "cost_per_success":
            continue  # no successful trials: cost per success is not defined
        if not finite(value):
            errors.append(f"{name}: metric {mid} is missing/non-finite/non-numeric")
    for mid in metric_ids:
        if mid not in metrics:
            errors.append(f"{name}: metric {mid} missing from summary")
    tags, by_item = {}, defaultdict(list)
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            errors.append(f"{name}: row {index} is not an object")
            continue
        item, seed = row.get("item_id"), row.get("seed")
        if (not isinstance(item, str) or not item or isinstance(seed, bool)
                or not isinstance(seed, int) or seed not in seeds):
            errors.append(f"{name}: invalid item/seed at row {index}")
            continue
        key = (item, seed)
        if key in pairs:
            errors.append(f"{name}: duplicate trial {item}@{seed}")
        pairs[key] = row
        by_item[item].append(row)
        slices = row.get("slices", [])
        if (not isinstance(slices, list) or any(not isinstance(s, str) for s in slices)
                or len(set(slices)) != len(slices)):
            errors.append(f"{name}: invalid slice tags for {item}@{seed}")
        else:
            current = frozenset(slices)
            if item in tags and tags[item] != current:
                errors.append(f"{name}: inconsistent slice tags across seeds for {item}")
            tags[item] = current
        for mid in graded:
            value = row.get(mid)
            if not finite(value) or value not in (0, 1):
                errors.append(f"{name}: missing/invalid grader {mid} at {item}@{seed}")
        for field, value in row.items():
            if isinstance(value, Real) and not finite(value):
                errors.append(f"{name}: non-finite {field} at {item}@{seed}")
        if "cost" in row and (not finite(row["cost"]) or row["cost"] < 0):
            errors.append(f"{name}: invalid cost at {item}@{seed}")
    if len(by_item) != count:
        errors.append(f"{name}: unique item count differs from manifest")
    if set(pairs) != {(item, seed) for item in by_item for seed in seeds}:
        errors.append(f"{name}: trials do not cover the item x seed Cartesian product")
    if errors:
        return errors, pairs

    # Recompute summaries from rows so a forged green aggregate cannot hide red evidence.
    expected = {}
    for mid in graded:
        values = [r[mid] for r in rows]
        expected[mid] = sum(values) if mid in ("approval_bypass", "secret_leak") else round(sum(values) / len(values), 4)
    if "pass_rate" in graded:
        passes = {item: sum(bool(r["pass_rate"]) for r in group) for item, group in by_item.items()}
        expected["pass_5"] = round(sum(c == len(by_item[item]) for item, c in passes.items()) / len(by_item), 4)
        for mid in metrics:
            for prefix, fn in (("pass_at_", stats.pass_at_k), ("pass_hat_", stats.pass_hat_k)):
                if mid.startswith(prefix):
                    try:
                        k = int(mid[len(prefix):])
                        expected[mid] = round(sum(fn(len(by_item[item]), c, k) for item, c in passes.items()) / len(by_item), 4)
                    except ValueError:
                        errors.append(f"{name}: cannot calculate {mid} from available seeds")
        if all("cost" in row for row in rows):
            successes = sum(passes.values())
            expected["cost_per_success"] = round(sum(r["cost"] for r in rows) / successes, 4) if successes else None
    for mid, value in expected.items():
        if mid in metrics and (value is None or metrics[mid] is None):
            if metrics[mid] is not value:
                errors.append(f"{name}: summary {mid} disagrees with rows")
        elif mid in metrics and not math.isclose(metrics[mid], value, rel_tol=0, abs_tol=1e-9):
            errors.append(f"{name}: summary {mid} disagrees with rows")
    return errors, pairs


def ratchet(spec: dict, base_spec: dict | None) -> list[str]:
    if base_spec is None or spec.get("eval_set_version") != base_spec.get("eval_set_version"):
        return []
    errors = []

    def compare(current, previous, key):
        if previous.get("blocking") and current.get("blocking") is not True:
            errors.append(f"RATCHET {key}: blocking removed")
        for direction in ("min", "max", "max_increase"):
            if direction not in previous:
                continue
            old, new = previous[direction], current.get(direction)
            if (not finite(new) or not finite(old)
                    or (new < old if direction == "min" else new > old)):
                errors.append(f"RATCHET {key}: {direction} loosened or removed")
        if previous.get("no_significant_drop") and current.get("no_significant_drop") is not True:
            errors.append(f"RATCHET {key}: no_significant_drop removed")

    for section in ("metrics", "slices"):
        def key(entry):
            return entry["id"] if section == "metrics" else (entry["name"], entry["metric"])
        entries = spec.get(section, [])
        current = {key(entry): entry for entry in entries}
        if len(current) != len(entries):
            errors.append(f"RATCHET {section}: duplicate definitions")
        for old in base_spec.get(section, []):
            identity = key(old)
            if identity not in current:
                errors.append(f"RATCHET {section}:{identity}: removed")
                continue
            new = current[identity]
            compare(new, old, f"{section}:{identity}")
            if section == "metrics":
                compare(new.get("threshold") or {}, old.get("threshold") or {}, f"metric:{identity}")
                for field in ("kind", "grader"):
                    if field in old and new.get(field) != old[field]:
                        errors.append(f"RATCHET metric:{identity}: {field} changed")
    return errors
