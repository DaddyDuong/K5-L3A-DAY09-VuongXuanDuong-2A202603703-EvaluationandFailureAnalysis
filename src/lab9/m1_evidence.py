"""Replay M1 evidence without changing Lab 8, public variants, or graders.

Run from src/: python -m lab9.m1_evidence
Output is supporting trace evidence, not an M4 eval report or baseline.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from lab8.shapes import SHAPES
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape

# Each probe isolates one supplied bug switch against the DB-trusting control.
# The event kind identifies the first observable wrong step; explanations live
# in docs/failure_taxonomy.md, rather than being inferred from a failure string.
PROBES = (
    ("FM-01", "leaky_trace", "C-010", "debug_claim_row"),
    ("FM-02", "ignore_denied", "C-007", "reply"),
    ("FM-03", "ticket_trust", "C-002", "model_override"),
    ("FM-04-sum", "sum_parts", "C-014", "proposal"),
    ("FM-04-round", "round_down", "C-001", "proposal"),
    ("FM-05", "pre_deducted", "C-014", "proposal"),
    ("FM-06", "stale_clause", "C-006", "quote"),
    ("FM-07", "sibling_refund", "C-011", "batch_refund"),
    ("FM-08", "misreport", "C-008", "reply"),
)


def capture(shape: str, claim_id: str, seed: int = 11) -> dict:
    case = investigate(shape, claim_id, seed)
    trial, label = case["trial"], case["label"]
    result = trial["result"]
    return {
        "run_id": result["run_id"], "shape": shape, "claim_id": claim_id, "seed": seed,
        "status": result["status"], "proposal_amount": result["proposal_amount"],
        "snapshot": trial["snapshot"], "unexpected_rows": trial["unexpected_rows"],
        "lab8_pass": trial["lab8_pass"], "lab8_reason": trial["lab8_reason"],
        "label": label,
        "events": [{"step": i, **event} for i, event in enumerate(trial["events"], 1)],
    }


def collect() -> dict:
    source = Path("data/public_claims.jsonl")
    claims = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
    controls = {claim["claim_id"]: capture("fixed", claim["claim_id"]) for claim in claims}
    if not all(control["lab8_pass"] for control in controls.values()):
        raise RuntimeError("A fixed control failed; inspect it before accepting M1 evidence")
    probes = {}
    for fm, bug, claim_id, first_kind in PROBES:
        shape = f"m1_{bug}"
        if shape in SHAPES:
            raise RuntimeError(f"Probe shape already registered: {shape}")
        SHAPES[shape] = make_shape(shape, {"no_override", bug})
        try:
            probe = capture(shape, claim_id)
        finally:
            del SHAPES[shape]
        probe["bug_switches"] = ["no_override", bug]
        probe["first_wrong_step"] = next(e["step"] for e in probe["events"] if e["kind"] == first_kind)
        probes[fm] = probe
    return {
        "schema": "m1_trace_evidence.v1",
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "world_sha256": hashlib.sha256(Path("data/public_world_state.json").read_bytes()).hexdigest(),
        "variant_agent_sha256": hashlib.sha256(Path("lab9/variant_agent.py").read_bytes()).hexdigest(),
        "seed": 11,
        "controls": controls,
        "probes": probes,
        "trace_case": capture("seeded_regression", "C-002"),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=Path("../docs/m1_trace_evidence.json"))
    args = parser.parse_args()
    evidence = collect()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {args.out}: {len(evidence['controls'])} fixed controls, {len(evidence['probes'])} isolated probes, 1 trace case")
    for fm, probe in evidence["probes"].items():
        print(f"  {fm}: {probe['run_id']} first wrong step={probe['first_wrong_step']}; Lab 8={probe['lab8_reason']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
