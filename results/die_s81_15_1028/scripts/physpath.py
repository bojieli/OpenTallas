#!/usr/bin/env python3
"""DIE-S81-15 estimate helper: add physical cell paths (die_trial tap_pad form) to an existing tree.json, so
trial_tap_arrivals exports every leg repeater as a tree-path node (start-tree retime candidates)."""
import json, sys
t = json.load(open(sys.argv[1])); po = t["parent_of"]; nb = {int(k): v for k, v in t["node_buf"].items()}
def cell_path(c):
    p = [c]
    while c in po:
        c = po[c]; p.append(c)
    return p[::-1]
t["node_stages"] = {c: len(cell_path(c)) for c in t["sites"]}
for x in t["taps"]:
    q = [c for c in po if po[c] == nb[x["node"]] and c.startswith("q") and c.endswith(x["port"])]
    x["driver"] = q[0] if q else nb[x["node"]]
    x["path"] = cell_path(x["driver"]); x["stages_from_root"] = len(x["path"])
json.dump(t, open(sys.argv[2], "w"))
print("taps", len(t["taps"]), "q-drivers", sum(1 for x in t["taps"] if x["driver"].startswith("q")))
