"""Use the NEW synthesized graph with existing placement and proposed source targets.

Usage: estimate_copy.py synth_geom.tsv old_placed_geom.tsv targets.tsv out.json
This is an estimate, not a post-placement census or timing gate.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/autopilot"))
import geom_rules as g

N, O = g.Design(sys.argv[1]), g.Design(sys.argv[2])
old = {c[6]: c for c in O.cells.values()}
targets = {}
for ln in open(sys.argv[3]):
    name, x, y = ln.rstrip().split("\t")
    targets[name] = (float(x), float(y))
missing = []
for i, c in list(N.cells.items()):
    p = targets.get(c[6])
    if p is None and c[6] in old:
        p = g.ctr(old[c[6]])
    if p is None and c[0] == "S":
        missing.append(c[6])
    if p:
        x, y = p
        w, h = c[4]-c[2], c[5]-c[3]
        N.cells[i] = (c[0], c[1], x-w/2, y-h/2, x+w/2, y+h/2, c[6])
if missing:
    raise SystemExit("unplaced sequential cells: " + repr(missing))
report = dict(kind="new-netlist placement ESTIMATE", **g.r2r_metrics(N))
Path(sys.argv[4]).write_text(json.dumps(report, indent=2) + "\n")
print(json.dumps(report))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
fig, ax = plt.subplots(figsize=(8, 11))
for c in O.cells.values():
    if c[0] == "M":
        ax.add_patch(Rectangle((c[2], c[3]), c[4]-c[2], c[5]-c[3],
                               facecolor="#dddddd", edgecolor="#555555", hatch="//"))
ax.scatter([p[0] for p in targets.values()], [p[1] for p in targets.values()],
           s=5, c="#0065a8", alpha=.35, label=f"{len(targets)} existing/copied stage targets")
def point(prefix):
    return next(p for n, p in targets.items() if n.replace("\\", "").startswith(prefix))
labels = {}
for prefix, text in [("u_cland_origin/s1$", "S1"), ("u_cland_rst_i/q$", "raw reset"),
                     ("u_cland_origin/s0$", "S0"), ("u_cland_origin/s2$", "original S2"),
                     ("u_cland_origin/g_export.g_copy[0].u_copy/q$", "export S2 copy"),
                     ("u_cland_fstart_o/q$", "existing START face FF")]:
    labels.setdefault(point(prefix), []).append(text)
if any(n.replace("\\", "").startswith("u_core.o_row[") for n in targets):
    labels.setdefault(point("u_core.o_row["), []).append("49-bit held result stage")
for p, names in labels.items():
    ax.scatter(*p, c="#d14900", s=35)
    ax.annotate("/".join(names), p, xytext=(-110 if p[0]>600 else 10, 15),
                textcoords="offset points", fontsize=8)
s1, copy = point("u_cland_origin/s1$"), point("u_cland_origin/g_export.g_copy[0].u_copy/q$")
ax.plot([s1[0], s1[0], copy[0]], [s1[1], copy[1], copy[1]], color="#d14900", lw=2,
        label="one-bit export path (M6/M7 above M5 cores)")
ax.set(xlim=(0, 708.48), ylim=(0, 1036.8), xlabel="um", ylabel="um",
       title="HEAD zero-cycle START state copy + existing-stage placement\n"
             f"NEW synthesized graph ESTIMATE: {report['r2r_captures_gt405']} captures >405um")
ax.set_aspect("equal")
ax.legend(loc="upper right", fontsize=8)
fig.tight_layout()
fig.savefig(Path(sys.argv[4]).with_suffix(".png"), dpi=150)
