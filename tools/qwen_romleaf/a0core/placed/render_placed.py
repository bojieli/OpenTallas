#!/usr/bin/env python3
"""QC-A0 10-24 A0 v8b PLACE-ONLY review: placed std-cell density per 10-um bin + regions + taps + cut ratios + hops.

  render_placed.py K INST_TSV REGIONS_TSV BUDGET_JSON TAPS_JSON DIAG_LOG OUT_PREFIX TITLE
Writes OUT_PREFIX.png (full tile + LSL-zone zoom) and OUT_PREFIX.json (density stats).
"""
import json
import re
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

K, INST, REG, BUD, TAPS, DIAG, OUT, TITLE = sys.argv[1:9]
W, H, BIN, TOP_Y = 457.92, 1157.76, 10.0, 653.04
PHYS = re.compile(r"TAPCELL|FILL|DECAP|TAP")
macs, cells = [], []
for l in open(INST):
    n, m, blk, x0, y0, x1, y1 = l.rstrip("\n").split("\t")
    x0, y0, x1, y1 = map(float, (x0, y0, x1, y1))
    (macs if blk == "1" else cells).append((n, m, x0, y0, x1, y1))
nx, ny = int(W // BIN) + 1, int(H // BIN) + 1
area = np.zeros((ny, nx)); seq = np.zeros((ny, nx))
SEQ = re.compile(r"^(DFF|SDF|DHL|DLL|ASYNC)")
for n, m, x0, y0, x1, y1 in cells:
    if PHYS.search(m):
        continue
    j, i = int(((y0 + y1) / 2) // BIN), int(((x0 + x1) / 2) // BIN)
    area[j, i] += (x1 - x0) * (y1 - y0)
    if SEQ.match(m):
        seq[j, i] += (x1 - x0) * (y1 - y0)
free = np.full((ny, nx), BIN * BIN)
HALO = 5.4
for n, m, x0, y0, x1, y1 in macs:
    hx0, hy0, hx1, hy1 = x0 - HALO, y0 - HALO, x1 + HALO, y1 + HALO   # rows cut under the macro + halo
    for j in range(max(0, int(hy0 // BIN)), min(ny, int(hy1 // BIN) + 1)):
        for i in range(max(0, int(hx0 // BIN)), min(nx, int(hx1 // BIN) + 1)):
            ox = max(0, min(hx1, (i + 1) * BIN) - max(hx0, i * BIN)); oy = max(0, min(hy1, (j + 1) * BIN) - max(hy0, j * BIN))
            free[j, i] -= ox * oy
for i in range(nx):       # die edge / core margin
    for j in range(ny):
        ox = max(0, min(W - 2.16, (i + 1) * BIN) - max(2.16, i * BIN)); oy = max(0, min(H - 2.16, (j + 1) * BIN) - max(2.16, j * BIN))
        free[j, i] = min(free[j, i], ox * oy)
ok = free > 20
util = np.where(ok, area / np.maximum(free, 1e-9), np.nan)
jt = int(TOP_Y // BIN)
st = {}
for nm, sl in (("all", slice(0, ny)), ("lsl_zone", slice(jt + 1, ny)), ("rom_zone", slice(0, jt))):
    u = util[sl][~np.isnan(util[sl])]
    st[nm] = dict(bins=int(u.size), mean=round(float(np.nansum(area[sl]) / np.sum(np.where(ok[sl], free[sl], 0))), 3),
                  p90=round(float(np.percentile(u, 90)), 3), p99=round(float(np.percentile(u, 99)), 3),
                  max=round(float(u.max()), 3), bins_gt_0p8=int((u > 0.8).sum()), bins_gt_0p9=int((u > 0.9).sum()))
hot = []
for j in range(ny):
    for i in range(nx):
        if ok[j, i] and util[j, i] > 0.8:
            hot.append([i * BIN, j * BIN, round(float(util[j, i]), 3)])
st["hot_bins_gt_0p8"] = sorted(hot, key=lambda h: -h[2])[:30]
st["std_cells"] = sum(1 for c in cells if not PHYS.search(c[1]))
regs = []
if REG.endswith(".tcl"):          # the kit regions tcl (3_place.odb keeps no dbRegion boxes)
    sys.path.insert(0, "/srv/opentallas-scratch2/claude/qc/a0v8place")
    import regions_parse as RP
    for g in RP.parse(REG):
        for b in g["boxes"]:
            regs.append(("qrl_" + g["name"], g["type"]) + tuple(b))
else:
    for l in open(REG):
        n, t, x0, y0, x1, y1 = l.rstrip("\n").split("\t")
        regs.append((n, t, float(x0), float(y0), float(x1), float(y1)))
# per region-box placed fill (all std cells whose centre is in the box / box row area outside macro halos)
def box_fill(x0, y0, x1, y1):
    a = sum((c[4] - c[2]) * (c[5] - c[3]) for c in cells if not PHYS.search(c[1])
            and x0 <= (c[2] + c[4]) / 2 < x1 and y0 <= (c[3] + c[5]) / 2 < y1)
    sq = sum((c[4] - c[2]) * (c[5] - c[3]) for c in cells if SEQ.match(c[1])
             and x0 <= (c[2] + c[4]) / 2 < x1 and y0 <= (c[3] + c[5]) / 2 < y1)
    fa = (x1 - x0) * (y1 - y0)
    for n, m, mx0, my0, mx1, my1 in macs:
        fa -= max(0, min(x1, mx1 + HALO) - max(x0, mx0 - HALO)) * max(0, min(y1, my1 + HALO) - max(y0, my0 - HALO))
    return dict(fill=round(a / max(fa, 1e-9), 3), seq_fill=round(sq / max(fa, 1e-9), 3), free_um2=round(fa, 1))
st["region_fill"] = {f"{n}@{x0:.0f},{y0:.0f}": box_fill(x0, y0, x1, y1) for n, t, x0, y0, x1, y1 in regs if y1 > TOP_Y}
st["hub_fill"] = box_fill(205.848, 660.64, 316.84, 829.032)
# 20-um bins (less halo-edge quantisation than 10 um)
B2 = 20.0; n2x, n2y = int(W // B2) + 1, int(H // B2) + 1
a2 = np.zeros((n2y, n2x)); f2 = np.zeros((n2y, n2x))
for j in range(ny):
    for i in range(nx):
        a2[int(j * BIN // B2), int(i * BIN // B2)] += area[j, i]; f2[int(j * BIN // B2), int(i * BIN // B2)] += max(free[j, i], 0)
u2 = np.where(f2 > 80, a2 / np.maximum(f2, 1e-9), np.nan)
st["bins20"] = dict(max=round(float(np.nanmax(u2)), 3), p99=round(float(np.nanpercentile(u2, 99)), 3),
                    gt_0p8=int(np.nansum(u2 > 0.8)), gt_0p7=int(np.nansum(u2 > 0.7)),
                    hot=sorted([[i * B2, j * B2, round(float(u2[j, i]), 3)] for j in range(n2y) for i in range(n2x)
                                if not np.isnan(u2[j, i]) and u2[j, i] > 0.7], key=lambda h: -h[2])[:20])
bud = json.load(open(BUD))
taps = json.load(open(TAPS))["taps"]
hops = []
for l in open(DIAG):
    if not l.startswith("DIAG"):
        continue
    m = re.search(r"worst \(([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+), ([\d.]+)\)", l)
    if m:
        d, a, b, c, e = map(float, m.groups())
        hops.append((d, a, b, c, e, l.split("'")[1]))
hops.sort(reverse=True)

fig, axs = plt.subplots(1, 2, figsize=(20, 13), gridspec_kw=dict(width_ratios=[1, 1.35]))
for ax, (ylo, yhi) in zip(axs, ((0, H), (640, H))):
    im = ax.imshow(util, origin="lower", extent=[0, nx * BIN, 0, ny * BIN], cmap="viridis", vmin=0, vmax=1.0,
                   interpolation="nearest")
    for n, m, x0, y0, x1, y1 in macs:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=True, fc="lightgrey", ec="k", lw=0.6, alpha=0.9))
        lab = re.sub(r".*?(g_sl\\?\[\d\\?\]|g_rb\\?\[\d\\?\]\S*?g_col\\?\[\d\\?\]|u_node).*", r"\1", n).replace("\\", "")
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, lab.replace("g_", "").replace(".g_single.", " "), fontsize=6, ha="center")
    for n, t, x0, y0, x1, y1 in regs:
        if y1 < ylo:
            continue
        c = "orange" if re.search(r"qrl_hd|qrl_l2c", n) else "red" if re.search(r"qrl_[foq]\d|qrl_fltq", n) else "magenta"
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, ec=c, lw=0.8, ls="--"))
        if ylo > 0:
            ax.text(x0 + 0.5, y1 - 3, n.replace("qrl_", ""), fontsize=5.5, color=c)
    for t in taps:
        ax.plot(t["xy"][0], t["xy"][1], marker="^" if t.get("kind") != "grid" else "*", color="white", ms=5, mec="k")
    if ylo > 0:
        for d, a, b, c, e, cls in hops[:12]:
            ax.plot([a, c], [b, e], color="red" if d > 405 else "cyan", lw=0.8)
            ax.text(c, e, f"{cls} {d:.0f}", fontsize=5, color="red" if d > 405 else "cyan")
        s = bud["summary"]
        for k, (lo, hi) in dict(W_col=(100.656, 200.448), M_col=(200.448, 300.24), gap=(300.24, 335.664),
                                E_col=(335.664, 435.456)).items():
            if k in s:
                x = s[k]["x"]; r = s[k]["ratio"]
                ax.axvline(x, color="red" if r > 0.6 else "white", lw=0.6, ls=":")
                ax.text(x, yhi - 8 - 8 * list(("W_col", "M_col", "gap", "E_col")).index(k), f"{k} {r:.2f}", fontsize=7,
                        color="red" if r > 0.6 else "white", ha="center")
        for k in ("H_full.row0", "H_full.row01", "H_full.row1", "H_full.row12", "H_full.row2", "H_east.row0", "H_east.row01"):
            if k in s:
                y = s[k]["y"]; r = s[k]["ratio"]
                ax.axhline(y, color="red" if r > 0.6 else "white", lw=0.5, ls=":")
                ax.text(W + 2, y, f"{k} {r:.2f}", fontsize=6, color="red" if r > 0.6 else "k")
    ax.set_xlim(0, W + (60 if ylo > 0 else 0)); ax.set_ylim(ylo, yhi); ax.set_aspect("equal")
fig.colorbar(im, ax=axs, shrink=0.4, label="placed std-cell area / free row area per 10-um bin")
fig.suptitle(f"{TITLE}\nLSL zone: mean {st['lsl_zone']['mean']} p99 {st['lsl_zone']['p99']} max {st['lsl_zone']['max']} "
             f"bins>0.8 {st['lsl_zone']['bins_gt_0p8']} | ROM zone mean {st['rom_zone']['mean']} max {st['rom_zone']['max']} | "
             f"dashed: orange hub sub-boxes, red face/result/qlr3/fault boxes, magenta ROM-zone boxes; ^ taps, * grid taps; "
             f"lines: 12 longest head-word hops (red > 405 um)", fontsize=9)
fig.savefig(OUT + ".png", dpi=110)
json.dump(st, open(OUT + ".json", "w"), indent=1)
print(json.dumps({k: v for k, v in st.items() if k not in ("hot_bins_gt_0p8", "region_fill")}))
