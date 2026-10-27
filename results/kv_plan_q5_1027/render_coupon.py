#!/usr/bin/env python3
"""KV-PLAN-DELTA-3: render a bounded FT coupon GRT (ft_station_probe --bounded --segmented) as per-layer guide-demand
maps (nets crossing each 10.8-um gcell edge / raw tracks per gcell, i.e. track use before derate; 0.6 = plan gate), hard-core outlines,
FT station sites and GRT overflow windows.  usage: render_coupon.py PLAN.json PART RUN_DIR OUT.png [RUN_DIR2 ...]"""
import json, math, re, sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools/die_plan"))
import schema as S

plan, part, run, out = sys.argv[1:5]
P = S.Plan(S.load(plan), Path(plan))
meta = json.loads((Path(run) / "station_probe.json").read_text())
x0, y0, x1, y1 = meta["coupon_canvas_um"]; G = 10.8
nx, ny = round((x1 - x0) / G), round((y1 - y0) / G)
dem = {L: np.zeros((ny, nx)) for L in ("M4", "M5", "M6", "M7")}
seen = set()                                        # one count per (net, layer, gcell): guide boxes overlap
with open(Path(run) / "grt/route.guide") as f:
    for ln in f:
        a = ln.split()
        if len(a) == 1 and a[0] not in "()":
            seen = set(); continue
        if len(a) != 5 or a[4] not in dem: continue
        bx0, by0, bx1, by1 = (int(v) / 1000 for v in a[:4]); L = a[4]
        i0, i1 = int((bx0 - x0) / G + 1e-6), int((bx1 - x0) / G - 1e-6)
        j0, j1 = int((by0 - y0) / G + 1e-6), int((by1 - y0) / G - 1e-6)
        i0, i1, j0, j1 = max(i0, 0), min(i1, nx - 1), max(j0, 0), min(j1, ny - 1)
        if P.layers[L]["dir"] == "H":
            if i1 == i0: continue                      # via / pin-access box
            cells = [(j, i) for j in range(j0, j1 + 1) for i in range(i0, i1)]       # gcell EDGES (i -> i+1), as GRT counts
        else:
            if j1 == j0: continue
            cells = [(j, i) for j in range(j0, j1) for i in range(i0, i1 + 1)]
        for c in cells:
            if (L, c) in seen: continue
            seen.add((L, c)); dem[L][c] += 1
tracks = {L: G / P.layers[L]["pitch_um"] for L in dem}
util = {L: dem[L] / tracks[L] for L in dem}
# overflow windows (GRT congestion report)
ovf = []
rpt = Path(run) / "grt/congestion.rpt"
if rpt.is_file():
    txt = rpt.read_text()
    for m in re.finditer(r"violation type: (\w+) congestion.*?congestion:(\d+).*?bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)", txt, re.S):
        g = m.groups(); ovf.append((g[0], int(g[1]), *map(float, g[2:6])))
t = P.types[P.parts[part]["type"]]
cores = []
for h in t.get("hard_cores", []):
    if "origin_um" not in h: continue
    cx, cy = h["origin_um"]; w, hh = h["outline_um"]
    if h.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"): w, hh = hh, w
    pts = [P.to_die(part, (cx + dx, cy + dy)) for dx in (0, w) for dy in (0, hh)]
    cores.append((min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)))
sites = json.loads((Path(run) / "station_sites.json").read_text())
st = []
for rows in sites.values():
    for slot in rows.values():
        for row in slot: st += [P.to_die(part, tuple(xy)) for xy in row[::8]]
summ = json.loads(Path(sys.argv[5]).read_text())[Path(run).name] if len(sys.argv) > 5 else None
fig, axs = plt.subplots(1, 4, figsize=(22, 7.6), dpi=110)
for ax, L in zip(axs, dem):
    im = ax.imshow(util[L], origin="lower", extent=(x0, x1, y0, y1), cmap="magma_r", vmin=0, vmax=1.0, interpolation="nearest")
    for c in cores: ax.add_patch(Rectangle((c[0], c[1]), c[2] - c[0], c[3] - c[1], fill=False, ec="tab:blue", lw=0.6))
    bx = meta["part_bounds_um"]; ax.add_patch(Rectangle((bx[0], bx[1]), bx[2] - bx[0], bx[3] - bx[1], fill=False, ec="k", lw=1.0))
    if st: ax.scatter([p[0] for p in st], [p[1] for p in st], s=0.3, c="tab:green", alpha=0.4)
    for typ, cg, a, b, c, d in ovf:
        ax.add_patch(Rectangle((a, b), c - a, d - b, fill=True, fc="cyan", ec="cyan", lw=0.8))
    mx = util[L].max(); hot = (util[L] > 0.6).sum()
    lay = (summ or {}).get("layers", {}).get(L, {})
    ax.set_title(f"{L} ({P.layers[L]['dir']}) max use {mx:.2f}, gcells >0.6: {hot}\nGRT use {lay.get('use','?')}% ovf {lay.get('ovf','?')}", fontsize=9)
    ax.set_xticks([]); ax.set_yticks([])
fig.colorbar(im, ax=axs, shrink=0.7, label="guide demand / raw tracks per 10.8-um gcell (gate 0.6)")
fig.suptitle(f"{part} ({P.parts[part]['type']}) bounded FT coupon GRT, {Path(run).name}: blue = hard cores (OBS M4-M5), "
             f"green = FT station sites (1/8 shown), cyan = GRT overflow gcells ({len(ovf)})", fontsize=10)
fig.savefig(out, bbox_inches="tight"); print(out, {L: round(float(util[L].max()), 3) for L in util}, len(ovf))
for L in dem:
    j, i = np.unravel_index(np.argmax(dem[L]), dem[L].shape)
    print("MAX", L, int(dem[L][j, i]), "tracks", round(tracks[L], 1), "at", round(x0 + (i + .5) * G, 1), round(y0 + (j + .5) * G, 1), "grid", i, j, nx, ny)
print("SUM", {L: int(dem[L].sum()) for L in dem})
