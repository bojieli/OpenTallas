#!/usr/bin/env python3
"""QC-PG-MAP: per-class upper-deck load maps (die coords) from the R35 slice plan core census (cores.json).
Classes (PDNSim is linear -> superpose): S = signed cores at own vectorless W (spread over the plan outline);
A = A0 cores (qfd_tile_n[kl]_a0c) at 1 W/mm2; F = rest of every partition (flattened logic, su_lane_w, btab, stations) at 1 W/mm2.
usage: loads.py cores.json own.json OUTDIR"""
import json, sys
from pathlib import Path
d = json.load(open(sys.argv[1])); own = json.load(open(sys.argv[2])); out = Path(sys.argv[3]); out.mkdir(parents=True, exist_ok=True)
area = lambda r: (r[2] - r[0]) * (r[3] - r[1]) * 1e-6
S, A, F = [], [], []
for p in d["parts"]:
    if p["module"].startswith(("ot_qfd_serdes", "ot_qfd_ucie")) or p["type"].startswith("phy_"): continue
    F.append([p["rect"], 1.0])
for c in d["cores"]:
    r = c["rect"]; m = c["module"]
    if m in own:
        S.append([r, own[m] / area(r)]); F.append([r, -1.0])
    elif m in ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c"):
        A.append([r, 1.0]); F.append([r, -1.0])
for n, L in (("S", S), ("A", A), ("F", F)):
    (out / f"loads_{n}.json").write_text(json.dumps(L))
    print(n, len(L))
