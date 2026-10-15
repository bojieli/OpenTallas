#!/usr/bin/env python3
"""Collect exact four-rank field results and require the production reduction order.

Runs no field simulations. --wait observes existing jobs until every named
layer's four rank checks and tree combine are complete, or a timeout/failure.
"""
import argparse
import json
import time
from pathlib import Path
from types import SimpleNamespace
import field_all


def collect(root, layers):
    done, pending, failed = [], [], []
    for layer in layers:
        works = [root / f"L{layer:02d}_r{rank}" for rank in range(4)]
        checks = []
        for rank, work in enumerate(works):
            try:
                rec = json.loads((work / "check.json").read_text())
            except (OSError, json.JSONDecodeError):
                break
            valid = (rec.get("layer") == layer and rec.get("rank") == rank
                     and rec.get("verdict") == "PASS" and rec.get("region_runs", 0) > 0
                     and rec.get("rows_checked", 0) > 0
                     and rec.get("region_runs_missing") == 0
                     and rec.get("region_runs_failed") == 0
                     and rec.get("rows_not_equal_model") == 0 and not rec.get("mutant"))
            if not valid:
                failed.append({"layer": layer, "rank": rank, "check": rec})
                break
            checks.append(rec)
        if len(checks) != 4:
            pending.append(layer)
            continue
        target = root / f"combine_L{layer:02d}.json"
        try:
            combine = json.loads(target.read_text())
        except (OSError, json.JSONDecodeError):
            combine = {}
        if combine.get("required_order") != "tree":
            try:
                field_all.cmd_combine(SimpleNamespace(works=",".join(map(str, works)), out=str(target)))
                combine = json.loads(target.read_text())
            except (OSError, ValueError, AssertionError, KeyError) as error:
                failed.append({"layer": layer, "combine_error": str(error)})
                continue
        if combine.get("verdict") != "PASS" or not combine.get("tensors"):
            failed.append({"layer": layer, "combine": combine})
            continue
        done.append({"layer": layer, "ranks": checks, "combine": combine})
    return {"schema": "opentallas.s81.field_sweep.v1", "expected_layers": layers,
            "completed": done, "pending": pending, "failed": failed,
            "verdict": "FAIL" if failed else "PENDING" if pending else "PASS"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--layers", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--wait", action="store_true")
    parser.add_argument("--timeout", type=int, default=21600)
    args = parser.parse_args()
    layers = [int(v) for v in args.layers.split(",")]
    if not layers or len(set(layers)) != len(layers) or any(not 0 <= v < 40 for v in layers):
        raise ValueError("expected distinct backbone layers 0..39")
    import hdc_golden_v41 as V
    V.set_arith("chunk8")
    deadline = time.monotonic() + args.timeout
    previous = None
    while True:
        rec = collect(args.root, layers)
        args.out.write_text(json.dumps(rec, indent=1) + "\n")
        state = (rec["verdict"], len(rec["completed"]), len(rec["pending"]), len(rec["failed"]))
        if state != previous:
            print("FIELD_SWEEP", state, flush=True)
            previous = state
        if rec["verdict"] != "PENDING" or not args.wait or time.monotonic() >= deadline:
            return 0 if rec["verdict"] == "PASS" else 1 if rec["verdict"] == "FAIL" else 2
        time.sleep(30)


if __name__ == "__main__":
    raise SystemExit(main())
