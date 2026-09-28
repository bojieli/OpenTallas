#!/usr/bin/env python3
"""Real reduced-checkpoint index score slice into exact top-K selector."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
SOURCES = [
    "rtl/hdc/v41x/ot_hdc_v41x_idx_score_slice.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx.sv",
    "rtl/hdc/v41x/ot_hdc_v41x_idx_arith.sv",
    "rtl/hdc/ot_hdc_fastfp.sv",
    "rtl/hdc/ot_hdc_delay.sv",
    "rtl/hdc/v41/ot_hdc_tselect.sv",
    "rtl/hdc/v41/ot_hdc_tselect_q.sv",
    "rtl/test/tb_hdc_v41x_idx_score_select_checkpoint.sv",
    "tools/rtl_hdc_v41x_idx_campaign.py",
    "tools/hdc_golden_v41.py",
    "tools/rtl_v41x_idx_score_select_checkpoint.py",
]
PAT = re.compile(r"PASS checkpoint score\+topK scores=(\d+) selected=(\d+) cycles=(\d+) "
                 r"score_stalls=(\d+) first_score=(\d+) last_score=(\d+) "
                 r"first_select=(\d+) last_select=(\d+)")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", type=Path, default=Path(
        "/home/ubuntu/OpenTallas/build/models/deepseek-v4.1-flash-reduced-v2/"
        "model-00001-of-00001.safetensors"))
    args = ap.parse_args()
    spec = importlib.util.spec_from_file_location("ixcamp", ROOT / SOURCES[8])
    assert spec and spec.loader
    ix = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ix)
    toks = ix.vehicle_tokens(40, checkpoint=args.checkpoint)
    chosen = [next(t for t in toks if t["cls"] == f"vehicle.L{layer}" and len(t["keep"]) == 40)
              for layer in (20, 24)]
    with tempfile.TemporaryDirectory(prefix="v41-score-select-") as td:
        work = Path(td)
        ix.write_mems(work, chosen, 32, 1)
        top = []
        for tok in chosen:
            bits = np.asarray(tok["exp"], np.uint32)
            vals = ix.G.from_bits(bits << 16)
            winners = sorted(map(int, ix.G.topk_lowest_index(vals.astype(np.float64), 8)))
            top.extend((i, int(bits[i])) for i in winners)
        assert len(top) == 16
        (work / "top_idx.mem").write_text("\n".join(f"{i:04x}" for i, _ in top) + "\n")
        (work / "top_val.mem").write_text("\n".join(f"{v:04x}" for _, v in top) + "\n")
        exe = work / "tb"
        subprocess.run(["iverilog", "-g2012", "-s", "tb_hdc_v41x_idx_score_select_checkpoint",
                        "-o", str(exe), *[str(ROOT / p) for p in SOURCES if p.endswith(".sv")]], check=True)
        sim = subprocess.run(["vvp", str(exe)], cwd=work, capture_output=True, text=True, timeout=900)
        if sim.returncode:
            raise RuntimeError(sim.stdout[-4000:] + sim.stderr[-1000:])
        match = PAT.search(sim.stdout)
        if not match:
            raise RuntimeError(sim.stdout[-4000:] + sim.stderr[-1000:])
        values = list(map(int, match.groups()))
        gap_sweep = []
        for gap in (0, 1, 2, 3, 4, 6, 8, 12, 16, 24, 32, 40, 48):
            probe = subprocess.run(["vvp", str(exe), f"+GAP={gap}"], cwd=work,
                                   capture_output=True, text=True, timeout=120)
            gap_sweep.append({"gap_cycles": gap, "pass": bool(PAT.search(probe.stdout)),
                              "first_failure": next((line for line in probe.stdout.splitlines()
                                                     if "FATAL:" in line), None)})
        vector_sha = {p: hashlib.sha256((work / p).read_bytes()).hexdigest() for p in
                      ("idx_q.mem", "idx_k.mem", "idx_e.mem", "top_idx.mem", "top_val.mem")}
    assert values[0] == 80 and values[1] == 16 and values[3] > 0
    rec = {
        "schema": "opentallas.v41-idx-score-select-checkpoint.v1",
        "status": "pass_exact_reduced_real_checkpoint",
        "checkpoint_sha256": hashlib.sha256(args.checkpoint.read_bytes()).hexdigest(),
        "source_sha256": {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in SOURCES},
        "vector_sha256": vector_sha,
        "cases": [{"layer": int(t["cls"].split("L")[1]), "keys": 40,
                   "topk": [i for i, _ in top[c*8:(c+1)*8]]}
                  for c, t in enumerate(chosen)],
        "measurement": dict(zip(("scores", "selected", "cycles", "score_stalls",
                                "first_score", "last_score", "first_select", "last_select"), values)),
        "query_turnaround_probe": gap_sweep,
        "scope": "real reduced-checkpoint 32-head x 32-dim index query/key scores; NK4 scorer directly into W4 exact threshold selector, two segments, topK8, periodic valid/ready gate backpressure; no timed HBM reader or shipped 128-dim checkpoint claim",
    }
    target = ROOT / "results/rtl/v41_idx_score_select_checkpoint.json"
    target.write_text(json.dumps(rec, indent=2) + "\n")
    print(target)


if __name__ == "__main__":
    main()
