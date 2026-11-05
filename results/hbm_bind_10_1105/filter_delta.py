"""HBM-BIND-10: drop stale-base ops from a plan delta (C-form route chain carried an older hard-core set).
usage: filter_delta.py IN.json.gz OUT.json.gz"""
import json, gzip, sys, collections
DROP = {"hard_cores", "contents", "clock", "internal_stations", "cells"}
d = json.load(gzip.open(sys.argv[1], "rt")); keep = []; dropped = collections.Counter()
for op in d["ops"]:
    p = op[1]
    if p[0] == "partition_types" and len(p) > 2 and p[2] in DROP: dropped[p[2]] += 1; continue
    if p[0] == "die": dropped["die"] += 1; continue
    keep.append(op)
d["ops"] = keep; d["new_sha"] = None; d["note"] = "filtered: dropped " + json.dumps(dropped)
json.dump(d, gzip.open(sys.argv[2], "wt")); print("kept", len(keep), "dropped", dict(dropped))
