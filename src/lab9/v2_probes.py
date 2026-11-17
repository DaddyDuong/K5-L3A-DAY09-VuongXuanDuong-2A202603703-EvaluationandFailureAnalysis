"""Reproducible v2 counterexamples; does not change the public mutation suite.

Run from src/: python -m lab9.v2_probes
The cross-principal probe deliberately copies synthetic foreign-owner fixture
data into an otherwise correct trace, to test the real artifact leak scanner.
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

from lab8.db import connect
from lab8.shapes import SHAPES
from lab9.eval import load_spec, load_world, main as eval_main, make_task
from lab9.variant_agent import make_shape


def register() -> None:
    for name, bugs in {
        "v2_misreport_probe": {"no_override", "misreport"},
        "v2_quiet_override_probe": {"no_override", "quiet_override"},
    }.items():
        SHAPES[name] = make_shape(name, bugs)
    fixed = make_shape("v2_cross_principal_probe", {"no_override"})

    def cross_principal(claim_id, **kwargs):
        result = fixed(claim_id, **kwargs)
        conn = connect(kwargs["store_path"])
        try:
            row = conn.execute(
                "SELECT c.principal_id AS request_principal, o.principal_id AS order_principal, "
                "o.phone, o.internal_note FROM claims c JOIN orders o ON c.order_id=o.order_id "
                "WHERE c.claim_id=? AND c.principal_id != o.principal_id", (claim_id,)
            ).fetchone()
            if row is not None:
                path = Path(result.trace_path)
                trace = json.loads(path.read_text(encoding="utf-8"))
                trace["events"].append({"kind": "cross_principal_debug", "payload": dict(row)})
                trace["steps"] = len(trace["events"])
                path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")
        finally:
            conn.close()
        return result

    SHAPES["v2_cross_principal_probe"] = cross_principal


def cross_case() -> dict:
    register()
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    world, claims = load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="lab9-cross-") as tmp:
        trial = make_task("v2_cross_principal_probe", world, claims, labels, Path(tmp))(
            {"claim_id": "C-113", "seed": 11})
    return {"trial": trial, "label": labels["C-113"]}


def main() -> int:
    register()
    for shape in ("v2_misreport_probe", "v2_quiet_override_probe", "v2_cross_principal_probe"):
        code = eval_main(["--shape", shape, "--spec", "config/metric_spec_v2.yaml"])
        if code:
            return code
    case = cross_case()
    path = Path("../docs/v2_cross_principal_evidence.json")
    # Store the actual trace and ledger, not the repeated artifact blob.
    case["trial"].pop("blob")
    path.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
