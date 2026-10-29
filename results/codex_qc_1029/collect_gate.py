#!/usr/bin/env python3
"""Collect QC die-gate decisions without treating landed single-cycle INFO as a gate."""
import argparse
import hashlib
import json
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("gate", type=Path)
parser.add_argument("--out", required=True, type=Path)
args = parser.parse_args()
data = json.loads(args.gate.read_text())
summary = data["summary"]
out = {
    "artifact": str(args.gate),
    "artifact_sha256": hashlib.sha256(args.gate.read_bytes()).hexdigest(),
    "plan": data["plan"],
    "plan_sha256": data["plan_sha256"],
    "summary": summary,
    "landed_single_cycle_INFO": {},
    "actual_open_items": [],
}
for corner in ("TT", "FF"):
    landed = data["corners"][corner]["classes"]["landed"]
    out["landed_single_cycle_INFO"][corner] = {
        key: landed[key] for key in (
            "worst_setup_slack_ps", "setup_neg_pairs", "worst_setup",
            "worst_hold_slack_ps", "hold_neg_pairs", "plan_landing",
        )
    }
if summary["core_insertion"]["verdict"] == "FAIL":
    out["actual_open_items"].append({
        "item": "early core taps without matching real views",
        "source": summary["core_insertion"]["source"],
        "owner": "QC-A0-KITS / QC die owner",
    })
for cls in ("intra", "seam"):
    real = summary[cls].get("real_view", {})
    if real.get("ff_hold_ps") is not None and real["ff_hold_ps"] < 0:
        out["actual_open_items"].append({
            "item": f"{cls} FF hold on real-view endpoints",
            "ps": real["ff_hold_ps"],
            "owner": "QC die owner; signed-view replacement then legal data hold repair",
        })
if summary["landed"]["verdict"] != "PASS":
    out["actual_open_items"].append({
        "item": "count-aligned crossing gate", "owner": "QC die owner / TOK-QC",
    })
args.out.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps({"landed_gate": summary["landed"]["verdict"],
                  "open": out["actual_open_items"]}, indent=2))
