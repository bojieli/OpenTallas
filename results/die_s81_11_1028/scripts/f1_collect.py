#!/usr/bin/env python3
"""DIE-S81-11 COLLECT FLOW joint4 (codex-relay-roads-1028/joint4): stats of the packing proposal + render.
Reads allocated_sites.json, priced_paths.json, endpoint_net_graph_v2.json (original placement), dump.json (macros)."""
import json, sys, math
J = sys.argv[1]; OUT = sys.argv[2]
a = json.load(open(J + "/allocated_sites.json")); p = json.load(open(J + "/priced_paths.json"))
g = json.load(open(J + "/endpoint_net_graph_v2.json"))["cells"]; dm = json.load(open(J + "/dump.json"))
mv = []
for c, v in a.items():
    o = g.get(c, {}).get("origin_um")
    if o: mv.append((abs(v["origin_um"][0] - o[0]) + abs(v["origin_um"][1] - o[1]), c, g[c]["master"]))
mv.sort()
ff = [m for m in mv if "DFF" in m[2] or "_DFF_" in m[1]]
wl = sorted(q["wire_length_um"] for q in p)
st = dict(cells=len(a), matched=len(mv), not_in_graph=len(a) - len(mv), paths=len(p), paths_fail=sum(not q["pass"] for q in p),
          wire_p50=round(wl[len(wl)//2], 1), wire_max=round(wl[-1], 1), limit=p[0]["limit_um"],
          move_L1_p50=round(mv[len(mv)//2][0], 2), move_L1_p99=round(mv[int(.99*len(mv))][0], 2), move_L1_max=round(mv[-1][0], 2),
          ff_moved=len(ff), ff_move_max=round(max(m[0] for m in ff), 2) if ff else None,
          masters={})
for m in mv:
    k = m[2].split("_")[0]; st["masters"][k] = st["masters"].get(k, 0) + 1
print(json.dumps(st, indent=1)); json.dump(st, open(OUT + "/f1_joint4_stats.json", "w"), indent=1)
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
fig, ax = plt.subplots(figsize=(12, 12))
for m in dm["macros"]:
    bb = m[2:6]
    if True:
        ax.add_patch(plt.Rectangle((bb[0], bb[1]), bb[2]-bb[0], bb[3]-bb[1], fc="#ddd", ec="#888", lw=0.5))
ox = [g[c]["origin_um"][0] for c in a if c in g]; oy = [g[c]["origin_um"][1] for c in a if c in g]
nx = [a[c]["origin_um"][0] for c in a if c in g]; ny = [a[c]["origin_um"][1] for c in a if c in g]
ax.scatter(ox, oy, s=1, c="tab:red", label="original"); ax.scatter(nx, ny, s=1, c="tab:blue", label="joint4 proposal")
for q in p[::7]:
    for l in q["legs"]:
        ax.plot([l["from_um"][0], l["to_um"][0]], [l["from_um"][1], l["to_um"][1]], c="tab:green", lw=0.2, alpha=0.4)
ax.set_aspect("equal"); ax.legend(markerscale=8); ax.set_title("FLOW joint4 F1 packing proposal (col_h9_r1): cells + 1/7 of road legs")
fig.savefig(OUT + "/f1_joint4.png", dpi=110)

