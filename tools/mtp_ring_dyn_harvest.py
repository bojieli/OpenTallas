#!/usr/bin/env python3
"""Collect immutable terminal ring-DYN campaign evidence on its compute host.

This is a metadata collector, not a build or simulation launcher. A negative
control requires the completed 18-output simulator and its protocol fault;
compiler failure or an absent PASS cannot qualify the control.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, required=True)
    p.add_argument("--scratch", type=Path, required=True)
    p.add_argument("--campaign", type=int, required=True)
    p.add_argument("--negative", action="store_true")
    p.add_argument("--output", type=Path, required=True)
    a = p.parse_args()
    tool = a.source / "tools/mtp_exact_wavefront2.py"
    spec = importlib.util.spec_from_file_location("pinned_wavefront", tool)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    tag = "stage2_wf_w0_deep_ringdyn" if a.negative else "stage2_wfc_w1_deep_ringdyn"
    receipt = a.scratch / f"run_{tag}.json"
    log = a.scratch / f"out_{tag}.txt"
    meta = json.loads(receipt.read_text())  # missing receipt means nonterminal
    metrics = mod.analyse(log.read_text())
    full = (meta["rc"] == 0 and metrics["out_msgs"] == 18
            and len(metrics["jobs"]) == 36 and metrics["total_cycles"] is not None)
    exact = all(metrics[k] == 0 for k in ("out_mismatch", "state_mismatch"))
    # The pinned bench increments its generic bad counter once for protocol=11.
    # Thus the expected negative has mismatches=1 despite exact payload/state.
    passed = (full and exact and metrics["mismatches"] == 1
              and not metrics["passed"] and metrics["proto_fault"]
              if a.negative else full and exact and metrics["mismatches"] == 0
              and metrics["passed"] and not metrics["proto_fault"])
    paths = [receipt, log, a.scratch / "prepare_stage2_deep.json"]
    prep = json.loads(paths[-1].read_text())
    expected_layers = [[14], [15]] if a.campaign in (14, 15) else [[19], [20]]
    if a.campaign not in (14, 15, 19, 20):
        raise ValueError("Only original campaigns 14, 15, 19, 20 are qualified")
    matched_vehicle = (prep["layers"] == expected_layers and len(prep["jobs"]) == 18
                       and meta["wave"] == (0 if a.negative else 1)
                       and meta["ctrl"] == ("wf" if a.negative else "wfc")
                       and bool(meta["rollback_ring_dyn"]))
    phase_log = a.scratch.parent / ("admitted_negative.log" if a.negative else "admitted_positive.log")
    if phase_log.exists():
        paths.append(phase_log)
    paths.extend(sorted((a.scratch / "cfg_stage2_deep").glob("*.hex")))
    result = dict(schema="opentallas.mtp_ring_dyn_terminal.v1", campaign=a.campaign,
                  role="negative_protocol_control" if a.negative else "positive_exactness",
                  gate_passed=bool(passed), run=meta, metrics=metrics,
                  source=dict(core_sha256=digest(a.source / "rtl/hdc/v41x/ot_hdc_core_v41x.sv"),
                              tool_sha256=digest(tool)),
                  collector_sha256=digest(Path(__file__)),
                  artifacts=[dict(path=str(f), sha256=digest(f)) for f in paths],
                  scope="Original two-stage 18-job ring8 fixture; native production shape and full-die closure are not qualified",
                  physical="Repair rides consuming sequencer contextual qualification; no standalone route")
    result["source_receipt_matches"] = result["source"]["core_sha256"] == meta["core_sha256"]
    result["campaign_vehicle_matches"] = matched_vehicle
    result["gate_passed"] &= result["source_receipt_matches"] and matched_vehicle
    with a.output.open("x") as f:  # preserve any prior verdict
        json.dump(result, f, indent=2)
        f.write("\n")
    print(json.dumps({"campaign": a.campaign, "gate_passed": result["gate_passed"],
                      "cycles": metrics["total_cycles"], "protocol_fault": metrics["proto_fault"]}))
    return 0 if result["gate_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
