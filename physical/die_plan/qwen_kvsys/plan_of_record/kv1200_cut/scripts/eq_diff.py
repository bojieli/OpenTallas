#!/usr/bin/env python3
"""EQ-by-construction check of the delta steps: only hard_cores origin_um/orient/track_offset_um/note and core-tap xy
may differ between A and B; prints a summary and exits 1 on any other difference."""
import json, sys
a = json.load(open(sys.argv[1])); b = json.load(open(sys.argv[2])); bad = []; moved = 0
OK_HC = {"origin_um", "orient", "track_offset_um", "note"}
def walk(x, y, p):
    if isinstance(x, dict) and isinstance(y, dict):
        for k in set(x) | set(y): walk(x.get(k), y.get(k), p + [k])
    elif isinstance(x, list) and isinstance(y, list) and len(x) == len(y):
        for i, (u, v) in enumerate(zip(x, y)): walk(u, v, p + [i])
    elif x != y:
        bad.append(p)
walk({k: v for k, v in a.items() if k != "partition_types"}, {k: v for k, v in b.items() if k != "partition_types"}, [])
for tn in set(a["partition_types"]) | set(b["partition_types"]):
    ta, tb = a["partition_types"].get(tn), b["partition_types"].get(tn)
    bad_before = len(bad); walk(ta, tb, [tn])
    new = bad[bad_before:]; del bad[bad_before:]
    for p in new:
        if len(p) >= 4 and p[1] == "hard_cores" and p[3] in OK_HC: moved += 1; continue
        if len(p) >= 5 and p[1] == "clock" and p[2] == "taps" and p[4] == "xy" and (ta["clock"]["taps"][p[3]].get("kind") == "core"): continue
        bad.append(p)
print("position/orient fields changed:", moved, "| other changes:", len(bad))
for p in bad[:20]: print("  NOT EQ:", "/".join(map(str, p)))
sys.exit(1 if bad else 0)
