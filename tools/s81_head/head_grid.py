#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-2: s81_head global-tree drive grid = the eB in-core island (plan core tap u_eB) of every hd_tile,
die frame, + the plan clock spine root as source.  Writes {"drivers", "root"} for qc_clk_mesh3.py grid."""
import json, sys
P = json.load(open(sys.argv[1]))
t = P["partition_types"]["hd_tile"]
w, h = t["outline_um"]
eb = [tp for tp in t["clock"]["taps"] if tp["name"].endswith("u_eB.clk")][0]["xy"]
def tf(q, x, y):
    o = q["orient"]; ox, oy = q["origin_um"]
    return {"R0": (ox + x, oy + y), "MY": (ox + w - x, oy + y), "MX": (ox + x, oy + h - y), "R180": (ox + w - x, oy + h - y)}[o]
drv = sorted({tuple(round(v, 4) for v in tf(q, *eb)) for q in P["partitions"] if q["type"] == "hd_tile"})
root = P["clock"]["spine"]["root_um"]
json.dump(dict(drivers=[list(d) for d in drv], root=root, source="hd_tile u_eB centre entry (plan clock tap), "
               "die frame; root = plan clock.spine.root_um"), open(sys.argv[2], "w"), indent=0)
xs = sorted({d[0] for d in drv}); ys = sorted({d[1] for d in drv})
print(len(drv), "drivers", len(xs), "cols", len(ys), "rows", "root", root)
print("cols", xs); print("rows", ys)
