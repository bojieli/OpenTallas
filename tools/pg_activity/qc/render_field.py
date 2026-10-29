#!/usr/bin/env python3
"""QC-PG-5 render: die overview (A0 outlines, 75-um field rects, IO windows, channels) + zoom at the field N edge."""
import sys, json
from pathlib import Path
sys.path.insert(0, sys.argv[1] + "/tools/die_plan")
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import die_trial as D, schema as S, infra_pg as I
plan, cores, out = sys.argv[2], sys.argv[3], Path(sys.argv[4])
P = S.Plan(S.load(plan), plan); io = I._pg_io(P, "."); cfg = D.bump_contract(P)
b = D.bump_grid(P, io, pads=True)
a0 = [c["rect"] for c in json.load(open(cores))["cores"] if c["module"] in ("qfd_tile_nk_a0c", "qfd_tile_nl_a0c")]
def base(ax):
    for r in a0: ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc="#cfe3ff", ec="#3060a0", lw=0.3))
    for f in cfg["fields"]:
        for r in f["rects_um"]: ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc="none", ec="red", lw=1.2))
    for w in io: r = w["rect_um"]; ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc="#ffd0a0", ec="orange", lw=0.8))
    for c in P.die.get("channels", []):
        if "rect_um" in c: r = c["rect_um"]; ax.add_patch(Rectangle((r[0], r[1]), r[2]-r[0], r[3]-r[1], fc="#dddddd", ec="grey", lw=0.5))
fig, ax = plt.subplots(figsize=(12, 10)); base(ax)
c = [x for x in b if x[3] == cfg["pad_um"]]
ax.scatter([x[1] for x in c], [x[2] for x in c], s=0.3, c="k", label=f"150-um base kept {len(c)}")
ax.set_xlim(0, P.W); ax.set_ylim(0, P.H); ax.set_aspect("equal")
ax.set_title(f"QC plan PG: 75-um field (red rects, {len(b)-len(c)} bumps) over the A0 array (blue), 150-um base (black dots)")
ax.legend(loc="upper right"); fig.savefig(out / "field_die.png", dpi=110); plt.close(fig)
for name, win in (("edgeN", (26352, 9504, 27852, 11004)), ("west", (0, 3000, 3000, 6000))):
    fig, ax = plt.subplots(figsize=(10, 10)); base(ax)
    for x in b:
        if win[0] <= x[1] <= win[2] and win[1] <= x[2] <= win[3]:
            h = x[3] / 2
            ax.add_patch(Rectangle((x[1]-h, x[2]-h), 2*h, 2*h, fc=("#30a030" if x[0] == "VDD" else "#a03030"), ec="k", lw=0.2, alpha=0.8))
    ax.set_xlim(win[0], win[2]); ax.set_ylim(win[1], win[3]); ax.set_aspect("equal")
    ax.set_title(f"{name}: pads drawn to size (green VDD / red VSS); 70-um base vs 37.5-um field")
    fig.savefig(out / f"field_{name}.png", dpi=90); plt.close(fig)
print("ok")
