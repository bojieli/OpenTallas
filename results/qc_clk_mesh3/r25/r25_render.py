"""R25: render the re-planned mesh (drop M9 row segments, band drivers, W-edge driver column) at a fix site.
usage: r25_render.py PLAN_JSON R2 R3B QCDIR OUT.png x0,y0,x1,y1"""
import json, sys
from pathlib import Path
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
pj, r2, r3b, qc, out, box = sys.argv[1:7]
sys.path.insert(0, qc)
import qc_clk_mesh as Q1
bx = [float(v) for v in box.split(",")]
D = json.load(open(pj)); rec = json.load(open(r2)); R3 = json.load(open(r3b))
pkg = str(Path(r2).resolve().parents[2])
P, dtp, parts, cores, psha = Q1.load(rec["plan"].replace("/w/", pkg + "/"), rec["tree_plan"].replace("/w/", pkg + "/"))
inb = lambda x, y: bx[0] <= x <= bx[2] and bx[1] <= y <= bx[3]
fig, ax = plt.subplots(figsize=(12, 14))
for p in parts:
    if p[2] >= bx[0] and p[0] <= bx[2] and p[3] >= bx[1] and p[1] <= bx[3]:
        ax.add_patch(Rectangle((p[0], p[1]), p[2] - p[0], p[3] - p[1], fill=False, ec="0.6", lw=0.8, ls="--"))
for c in cores:
    if c[2] >= bx[0] and c[0] <= bx[2] and c[3] >= bx[1] and c[1] <= bx[3]:
        ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fc="#f3e7c9" if c[6].endswith("a0c") else "#e0e0e0", ec="0.4", lw=0.6))
for (y, xl, xh) in D["H8"]:
    if bx[1] <= y <= bx[3]:
        ax.plot([max(xl, bx[0]), min(xh, bx[2])], [y, y], color="tab:blue", lw=0.7)
dset = set()
for (x, yl, yh) in D["V9"]:
    if bx[0] <= x <= bx[2] and yh >= bx[1] and yl <= bx[3]:
        drop = yh - yl < 2000
        ax.plot([x, x], [max(yl, bx[1]), min(yh, bx[3])], color="tab:red" if drop else "tab:purple", lw=1.4 if drop else 0.9)
        if drop:
            for yy in (yl, yh):
                if inb(x, yy):
                    ax.plot([x], [yy], marker="_", color="k", ms=6)
for n in rec["nodes"]:
    if n["driver"] and inb(*n["site"]):
        ax.plot([n["site"][0]], [n["site"][1]], "s", color="tab:green", ms=3)
for d in D["drivers"]:
    if inb(d["x"], d["y"]):
        ax.plot([d["x"]], [d["y"]], "D" if d["kind"] == "band" else "s", color="darkorange" if d.get("mult", 1) == 2 else ("gold" if d["kind"] == "band" else "magenta"),
                ms=6 if d.get("mult", 1) == 2 else 4, mec="k", mew=0.4)
CH = 1157.76
for q in R3["lattices"]["R23_d51_candidate"]["per_instance"]:
    for n, t in R3["islands"].items():
        u, v = t["drop_core_frame"]; x, y = q["x0"] + u, q["y0"] + (CH - v if q["mx"] else v)
        if inb(x, y):
            ax.plot([x], [y], "o", color="k", ms=1.8)
ax.set_xlim(bx[0], bx[2]); ax.set_ylim(bx[1], bx[3]); ax.set_aspect("equal")
ax.set_title("R25 mesh re-plan: red = drop M9 row segments (end ticks), purple = kept/driver-column M9, blue = M8;\n"
             "green = R23 column drivers, magenta = W-edge column drivers, gold = band drivers (orange = x2 sizing), black dots = A0 island drops;\n"
             "tan = A0 cores, grey = other hard cores, dashed = partitions", fontsize=8)
fig.savefig(out, dpi=110, bbox_inches="tight")
print("wrote", out)
