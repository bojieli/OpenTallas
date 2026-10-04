#!/usr/bin/env python3
"""HA3: assemble the measured record (results/rtl/hbm_accel_ha3_20261004/measured.json) from the system runs, their
per-collective section measurements, the epilogue gate and the physical in-context results, with the per-user gain
projection and the verdicts.  Inputs are the JSON files the other HA3 tools wrote (paths on the command line).

    python3 tools/hbm_accel_ha3_record.py --qwen-measure q.json --ds-measure d.json --qwen-runs DIR --ds-runs DIR \
        --gate gate.json [--phys DIR] --out results/rtl/hbm_accel_ha3_20261004/measured.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
F_SM = 1.2e9
# full-shape ablation model (claude/hbm-accelerator-study-20261003 ladder_model.py): DS AR token parts (us) and counts
DS_AR_US = dict(sm=70.58, barrier=22.29, collective=240.46, local=103.48, fetch=5.33)
DS_COLLECTIVES = 265
DS_MODEL_R3A_NS = 148 / 2 / 1.09864           # the transferred Qwen ROM cut-through figure, ns per collective
DS_MODEL_R3B_US = 6.1
QWEN_LAYERS, QWEN_AR_PER_LAYER = 36, 2


def load(p):
    return json.loads(Path(p).read_text())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--qwen-measure", required=True)
    ap.add_argument("--ds-measure", required=True)
    ap.add_argument("--qwen-runs", required=True)
    ap.add_argument("--ds-runs", required=True)
    ap.add_argument("--gate", required=True)
    ap.add_argument("--phys")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    qm, dm, gate = load(a.qwen_measure), load(a.ds_measure), load(a.gate)
    runs = {}
    for d in (a.qwen_runs, a.ds_runs):
        for p in sorted(Path(d).glob("run_*.json")):
            r = load(p)
            runs[f"{r['model']}:{p.stem[4:]}"] = dict(
                mode=r["mode"], ha3=r["ha3"], flat=r.get("flat", 5), status=r["status"], clk_sm_cycles=r["clk_sm_cycles"],
                steps=[(s["pos"], s["next"], s["status"], s["step_cycles"]) for s in r["steps"]],
                expected=[(s["pos"], s["next"]) for s in r["expected_steps"]], wall_seconds=r["wall_seconds"],
                source_sha256=r["source_sha256"])
    rec = dict(schema="opentallas.hbm_accel.ha3_measured.v1",
               source_commit=subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True,
                                            text=True).stdout.strip(),
               runs=runs, qwen_sections=qm, ds_sections=dm,
               epilogue_gate=dict(status=gate["status"], counts=gate["counts"], n_cases=gate["n_cases"],
                                  resolves=gate["resolves"]))
    if a.phys:
        rec["physical"] = {p.stem: load(p) for p in sorted(Path(a.phys).glob("*.json"))}
    Path(a.out).write_text(json.dumps(rec, indent=1) + "\n")
    print("wrote", a.out)


if __name__ == "__main__":
    main()
