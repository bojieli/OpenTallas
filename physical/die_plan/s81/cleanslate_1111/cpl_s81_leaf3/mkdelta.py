#!/usr/bin/env python3
"""CPL-S81-LEAF-3: per-family delta {type:{inst:[x,y,orient]}} + sidecar (changed type keys) from a chosen core_place
arm.  usage: mkdelta.py BASE_PLAN OUTDIR FAM=TYPE=ARM_PLAN [...]"""
import hashlib, json, sys
from pathlib import Path
B = json.load(open(sys.argv[1]))["partition_types"]
out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
cache = {}
for spec in sys.argv[3:]:
    fam, tn, pp = spec.split("=", 2)
    if pp not in cache:
        cache[pp] = json.load(open(pp))["partition_types"]
    T1 = cache[pp][tn]
    h0 = {h["inst"]: h for h in B[tn]["hard_cores"]}
    d = {h["inst"]: [h["origin_um"][0], h["origin_um"][1], h.get("orient", "R0")] for h in T1["hard_cores"]
         if h["origin_um"] != h0[h["inst"]]["origin_um"] or h.get("orient", "R0") != h0[h["inst"]].get("orient", "R0")}
    side = {k: v for k, v in T1.items() if v != B[tn].get(k)}
    (out / (fam + ".delta.json")).write_text(json.dumps({tn: d}, indent=1, sort_keys=True) + "\n")
    (out / (fam + ".types_after.json")).write_text(json.dumps({tn: side}, sort_keys=True) + "\n")
    print(fam, tn, "moved", len(d), "keys", sorted(side), hashlib.sha256((out / (fam + ".delta.json")).read_bytes()).hexdigest()[:16])
