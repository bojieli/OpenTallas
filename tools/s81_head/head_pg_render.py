#!/usr/bin/env python3
"""INFRA-FIRST-HEAD-5 render: (1) hd_tile zoom with die PG M9 VDD/VSS straps (plan die.pg.grid), the 150-um C4 power
bump pads (pad edge PAD um, checkerboard), the M9 clock mesh straps re-snapped to the plan's VSS-locked lanes, the M8
clock rows and the hard cores; (2) co-located VDD+VSS PDNSim map of one window kit.
    head_pg_render.py PLAN --straps straps.json --ir KITDIR --pad 75 --out DIR"""
import argparse, csv, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "die_plan")); sys.path.insert(0, str(ROOT / "tools" / "s81_head"))
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import die_trial as D, infra_pg as G, schema as S, head_mesh_r3 as M

ap = argparse.ArgumentParser(); ap.add_argument("plan"); ap.add_argument("--straps", required=True)
ap.add_argument("--ir", required=True); ap.add_argument("--pad", type=float, default=75.0); ap.add_argument("--out", required=True)
ap.add_argument("--zoom", default="4532.48,6531.84,5240.96,7568.64", help="x0,y0,x1,y1 (default: one hd_tile)")
a = ap.parse_args(); od = Path(a.out); od.mkdir(parents=True, exist_ok=True)
raw = json.loads(Path(a.plan).read_text()); P = S.Plan(S.load(a.plan), Path(a.plan))
g9 = next(g for g in raw["die"]["pg"]["grid"] if g["layer"] == "M9"); g8 = next(g for g in raw["die"]["pg"]["grid"] if g["layer"] == "M8")
Sx, jog = M.snap_lanes([tuple(s) for s in json.loads(Path(a.straps).read_text())], raw)
zx0, zy0, zx1, zy1 = map(float, a.zoom.split(","))
fig, ax = plt.subplots(figsize=(10, 13))
# hard cores of the tiles in the zoom
T = raw["partition_types"]["hd_tile"]; tw, th = T["outline_um"]
for q in raw["partitions"]:
    ox, oy = q["origin_um"]; w, h = raw["partition_types"][q["type"]]["outline_um"]
    if ox > zx1 or ox + w < zx0 or oy > zy1 or oy + h < zy0: continue
    ax.add_patch(Rectangle((ox, oy), w, h, fill=False, ec="k", lw=1.2))
    ax.text(ox + 4, oy + h - 20, f"{q['name']} ({q['type']},{q['orient']})", fontsize=7)
    if q["type"] == "hd_tile":
        for c in T["hard_cores"]:
            x, y = c["origin_um"]; cx, cy = c["outline_um"]
            x = tw - x - cx if q["orient"] in ("MY", "R180") else x
            ax.add_patch(Rectangle((ox + x, oy + y), cx, cy, fc="#f4d9a6" if "elemB" in c["module"] else "#dde6f0", ec="#888", lw=0.6))
            ax.text(ox + x + 5, oy + y + 5, "elemB" if "elemB" in c["module"] else "elemA", fontsize=7)
# M9 PG straps (VDD at offset, VSS at offset + pitch/2)
p9, w9, o9 = g9["pitch_um"], g9["width_um"], g9["offset_um"]
k = int(zx0 // p9) - 1
while k * p9 < zx1 + p9:
    for c, col in ((o9 + k * p9, "#d62728"), (o9 + k * p9 + p9 / 2, "#1f77b4")):
        if zx0 - w9 < c < zx1 + w9: ax.add_patch(Rectangle((c - w9 / 2, zy0), w9, zy1 - zy0, fc=col, alpha=0.28, lw=0))
    k += 1
# bump pads
for net, x, y in D.bump_grid(P, G._pg_io(P, Path(a.plan).parent), pitch=150.0):
    if zx0 - a.pad < x < zx1 + a.pad and zy0 - a.pad < y < zy1 + a.pad:
        ax.add_patch(Rectangle((x - a.pad / 2, y - a.pad / 2), a.pad, a.pad, fill=False, ec="#d62728" if net == "VDD" else "#1f77b4", lw=1.6, ls="--"))
        ax.plot([x], [y], "o", ms=3, c="#d62728" if net == "VDD" else "#1f77b4")
# clock mesh straps (snapped)
for L, f, lo, hi, _k in Sx:
    if L == "M9" and zx0 <= f <= zx1: ax.plot([f, f], [max(lo, zy0), min(hi, zy1)], c="#2ca02c", lw=2.2)
    if L == "M8" and zy0 <= f <= zy1: ax.plot([max(lo, zx0), min(hi, zx1)], [f, f], c="#9467bd", lw=2.2)
ax.set_xlim(zx0, zx1); ax.set_ylim(zy0, zy1); ax.set_aspect("equal")
ax.set_title(f"s81_head PG: M9 VDD(red)/VSS(blue) {w9}@{p9}, M8 {g8['width_um']}@{g8['pitch_um']} (not drawn); 150-um C4 pads {a.pad:g} um (dashed);\n"
             f"clock mesh M9 (green) / M8 (purple) straps on VSS-locked lanes (max jog {max(jog):.2f} um)", fontsize=9)
fig.tight_layout(); fig.savefig(od / "pg_tile_zoom.png", dpi=110); plt.close(fig)
# IR map
m = json.loads((Path(a.ir) / "irwin.json").read_text()); x0, y0 = m["window_um"][:2]
def per(p, vdd):
    d = {}
    for r in csv.DictReader(open(p)):
        v = (0.7 - float(r["Voltage"]) if vdd else float(r["Voltage"])) * 1e3; n = r["Instance"]
        if v > d.get(n, (-1,))[0]: d[n] = (v, float(r["X location"]) + x0, float(r["Y location"]) + y0)
    return d
A, B = per(Path(a.ir) / "ir_VDD.csv", True), per(Path(a.ir) / "ir_VSS.csv", False)
xs = [A[n][1] for n in A]; ys = [A[n][2] for n in A]; vs = [A[n][0] + B[n][0] for n in A]
fig, ax = plt.subplots(figsize=(10, 9)); sc = ax.scatter(xs, ys, c=vs, s=9, marker="s", cmap="inferno")
plt.colorbar(sc, label="VDD drop + VSS bounce at the block (mV), above-M7 only")
x1, y1 = m["window_um"][2:]; ax.add_patch(Rectangle((x0 + 450, y0 + 450), x1 - x0 - 900, y1 - y0 - 900, fill=False, ec="c", lw=1.5, ls="--"))
for q in raw["partitions"]:
    ox, oy = q["origin_um"]; w, h = raw["partition_types"][q["type"]]["outline_um"]
    if ox < x1 and ox + w > x0 and oy < y1 and oy + h > y0: ax.add_patch(Rectangle((ox, oy), w, h, fill=False, ec="w", lw=0.5))
ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect("equal")
ax.set_title(f"{m['window']}: PDNSim co-located VDD+VSS, max {max(vs):.1f} mV (dashed = interior >=450 um from open window edges)", fontsize=9)
fig.tight_layout(); fig.savefig(od / "ir_colocated.png", dpi=100); plt.close(fig)
print("max jog", max(jog), "moved M9", sum(1 for s, j in zip(Sx, jog) if s[0] == "M9" and j > 1e-3))
