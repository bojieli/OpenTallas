#!/usr/bin/env python3
"""Check W13 column corner evidence before consuming its SS macro model.

This is a prerequisite for SM hardening, not an in-context SM sign-off.
Prints an audit to stdout; never rewrites physical records or starts jobs.
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


POLICY = "setup at SS with 60 ps uncertainty, hold at FF with 25 ps (AGENTS.md sign-off corners)"
CHIP = Path("results/physical_abi3/asap7/chip")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(root, block, expected_sources):
    path = root / CHIP / "corners" / f"{block}.json"
    issues, pins = [], {}
    if not path.is_file():
        return {"block": block, "passed": False, "issues": ["missing_corner_record"]}
    record = json.loads(path.read_text())
    if record.get("schema") != "opentallas-chip-block-corners-v1":
        issues.append("wrong_record_schema")
    if record.get("block") != block:
        issues.append("wrong_block")
    if record.get("clock_period_ps") != 833.0:
        issues.append("wrong_clock_period")
    if record.get("policy") != POLICY:
        issues.append("wrong_uncertainty_policy")
    if record.get("closed_signoff") is not True:
        issues.append("failed_signoff_verdict")
    sources = record.get("sources", [])
    if {s["path"] for s in sources} != set(expected_sources) or len(sources) != len(expected_sources):
        issues.append("source_list_mismatch")
    for source in sources:
        p = root / source["path"]
        if not p.is_file() or digest(p) != source["sha256"]:
            issues.append("source_pin_mismatch:" + source["path"])
    for corner, timing in (("SS", "setup"), ("FF", "hold")):
        view = record.get("corners", {}).get(corner, {})
        if view.get("rc") != 0:
            issues.append(corner + ":failed_or_missing_run")
        if view.get("macros_at_tt") != []:
            issues.append(corner + ":unqualified_macro_corner")
        for metric in (timing + "_wns_ps", timing + "_tns_ps"):
            value = view.get(metric)
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                issues.append(corner + ":invalid_" + metric)
        model = view.get("timing_model")
        expected = CHIP / "abstracts" / block / f"{block}_{corner.lower()}.lib"
        if model != str(expected) or not (root / expected).is_file():
            issues.append(corner + ":missing_or_wrong_timing_model")
        else:
            pins[str(expected)] = digest(root / expected)
    return {"block": block, "passed": not issues, "issues": issues,
            "record": str(path.relative_to(root)), "record_sha256": digest(path),
            "timing_model_sha256": pins}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--block", choices=("ot_gpu_tc_col", "ot_gpu_tc16", "ot_gpu_bd_col"), action="append", required=True)
    args = parser.parse_args()
    from tools.chip_assembly.floorplans import BLOCKS
    rows = [check(args.root.resolve(), name, BLOCKS[name].sources) for name in args.block]
    result = {"schema": "opentallas.w13.column_corner_gate.v1", "scope": "column corner prerequisite only; SM context and boundary closure remain required",
              "passed": all(row["passed"] for row in rows), "columns": rows,
              "tool_sha256": digest(Path(__file__))}
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
