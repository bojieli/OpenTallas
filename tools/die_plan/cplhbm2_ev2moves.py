#!/usr/bin/env python3
"""CPL-HBM-2: core_place event row cores_after (or a delta {type:{inst:[x,y,o]}}) -> cp_probe moves file.
usage: ev2moves.py PLAN TYPE SRC.json OUT.moves"""
import json, re, sys
plan, tn, src, out = sys.argv[1:5]
t = json.load(open(plan))["partition_types"][tn]
J = json.load(open(src))
if "rows" in J:
    ca = next(r for r in J["rows"] if r["type"] == tn)["cores_after"]
    ca = {k: (v["origin_um"][0], v["origin_um"][1], v["orient"]) for k, v in ca.items()}
else:
    ca = {k: tuple(v) for k, v in J[tn].items()}
L = ["# %s %s %s" % (plan, tn, src)]
for h in t["hard_cores"]:
    inst = h.get("physical_inst") or h["inst"]
    key = re.sub(r"[^A-Za-z0-9]+", "_", inst).strip("_")
    x, y, o = ca.get(h["inst"], (h["origin_um"][0], h["origin_um"][1], h.get("orient", "R0")))
    dx, dy = h.get("track_offset_um", [0, 0])
    L.append("%s %.4f %.4f %s" % (key, x + dx, y + dy, o))
open(out, "w").write("\n".join(L) + "\n")
print(len(L) - 1, "macros")
