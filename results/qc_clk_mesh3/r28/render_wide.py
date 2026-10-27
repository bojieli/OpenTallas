import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import schema, die_infra as I, die_clock_128 as C, die_clock_mesh as D
P = schema.Plan(schema.load(sys.argv[1]), Path(sys.argv[1])); m = json.load(open(sys.argv[2])); nd = D.NDR[m["ndr"]]
r = I.pg_rects(P, C.pg_grid(P))
segs = [("M8", s["x0"], s["y"], s["x1"], s["y"], "ck", "mesh") for s in m["M8"]] + [("M9", s["x"], s["y0"], s["x"], s["y1"], "ck", "mesh") for s in m["M9"]]
sh = C.clock_shapes(segs, nd, "VSS")
s0 = m["M8"][0]; cx, cy = s0["x0"], s0["y"]
fig, axs = plt.subplots(1, 2, figsize=(16, 8))
for ax, L in zip(axs, ("M8", "M9")):
    X0, Y0, X1, Y1 = cx - 15, cy - 15, cx + 15, cy + 15
    for n, l, a, b, c, d in r:
        if l == L and c > X0 and a < X1 and d > Y0 and b < Y1:
            ax.add_patch(Rectangle((a, b), c - a, d - b, color="red" if n == "VDD" else "blue", alpha=0.5))
    for L2, net, kind, p0, p1, a0, a1 in sh:
        if L2 != L: continue
        V = L == "M9"; x0, x1, y0, y1 = (p0, p1, a0, a1) if V else (a0, a1, p0, p1)
        if x1 > X0 and x0 < X1 and y1 > Y0 and y0 < Y1:
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color="lime" if kind == "mesh" else "black", alpha=0.9))
    ax.set_xlim(X0, X1); ax.set_ylim(Y0, Y1); ax.set_aspect("equal")
    ax.set_title(f"{L}: VDD red / VSS blue, clock strap green, VSS shield black (window at {cx:.2f},{cy:.2f})")
plt.tight_layout(); plt.savefig(sys.argv[3], dpi=80)
