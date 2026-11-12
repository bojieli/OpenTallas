#!/usr/bin/env python3
"""transplant.py BASE DELTA_PLAN OUT types : OUT = BASE with the listed types' hard_core origin_um and the whole clock
block taken from DELTA_PLAN (positions-only delta); every other byte (views, notes) stays BASE."""
import json, sys, copy
base = json.load(open(sys.argv[1])); dp = json.load(open(sys.argv[2])); out = sys.argv[3]
for T in sys.argv[4].split(","):
    bt = base["partition_types"][T]; dt = dp["partition_types"][T]
    pos = {h["inst"]: h["origin_um"] for h in dt["hard_cores"]}
    for h in bt["hard_cores"]:
        h["origin_um"] = copy.deepcopy(pos[h["inst"]])
    for k in ("taps", "added_taps", "tap_um", "landing_contract"):
        if k in dt.get("clock", {}): bt["clock"][k] = copy.deepcopy(dt["clock"][k])
json.dump(base, open(out, "w"), indent=1)
