#!/usr/bin/env python3
"""PNG renders for the B2r2 die trial (TRIAL-HBM visual review).

    python3 tools/die_trial/hbm_b2_render.py power --power power_map.json --out power_density.png
    python3 tools/die_trial/hbm_b2_render.py ir --power power_map.json --case DIR [--case DIR ...] --net VDD --out ir.png

ir: per-instance (load tile) voltages from each case's ir_<net>.rpt drawn in die coordinates (drop in mV for VDD,
rise for VSS); the full-die case (if given first) is the background, windows are drawn over it with a white outline;
partition outlines + names, keep-outs hatched, the worst inner node of each case marked.
"""
import argparse
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
import numpy as np  # noqa: E402

VDD = 0.7


def outlines(ax, pm, names=True, fs=4):
    for p in pm["partitions"]:
        x0, y0, x1, y1 = [v / 1000 for v in p["rect_um"]]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.4, ec="k"))
        if names:
            ax.text((x0 + x1) / 2, (y0 + y1) / 2, p["name"], ha="center", va="center", fontsize=fs, color="k", alpha=0.8)
    for s in pm["regions"]:
        if s["kind"] in ("hbm_phy", "serdes", "ucie"):
            x0, y0, x1, y1 = [v / 1000 for v in s["rect_um"]]
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, lw=0.8, ec="magenta", hatch="///"))


def power(a):
    pm = json.loads(Path(a.power).read_text())
    W, H = 25.19424, 18.3168
    fig, ax = plt.subplots(figsize=(10, 7.6), dpi=110)
    cmap = plt.get_cmap("viridis")
    vals = [p["w_per_mm2"] for p in pm["partitions"]] + [s["w_per_mm2"] for s in pm["regions"]]
    norm = matplotlib.colors.LogNorm(vmin=0.3, vmax=max(vals))
    for p in pm["partitions"]:
        x0, y0, x1, y1 = [v / 1000 for v in p["rect_um"]]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=cmap(norm(p["w_per_mm2"])), ec="k", lw=0.4))
    for s in pm["regions"]:
        x0, y0, x1, y1 = [v / 1000 for v in s["rect_um"]]
        io = s["kind"] in ("hbm_phy", "serdes", "ucie")
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=cmap(norm(s["w_per_mm2"])), ec="red" if io else "none", lw=1.2))
        if io:
            ax.annotate(f"{s['kind']} {s['w']:.1f} W\n{s['w_per_mm2']:.1f} W/mm2", ((x0 + x1) / 2, (y0 + y1) / 2), fontsize=5,
                        color="red", ha="center", va="center", xytext=(0, 14 if y0 > 1 else 16), textcoords="offset points",
                        arrowprops=dict(arrowstyle="-", color="red", lw=0.5))
    for p in pm["partitions"]:
        x0, y0, x1, y1 = [v / 1000 for v in p["rect_um"]]
        ax.text((x0 + x1) / 2, (y0 + y1) / 2, f"{p['name']}\n{p['w']:.1f}W", ha="center", va="center", fontsize=3.6, color="w")
    sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
    fig.colorbar(sm, ax=ax, label="W/mm2 (log)", fraction=0.03)
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
    ax.set_title(f"B2r2 ESTIMATED peak power density (a20, TT): total {pm['total_w']:.0f} W, avg {pm['avg_w_per_mm2']:.2f} W/mm2; red = IO PHY", fontsize=8)
    fig.tight_layout(); fig.savefig(a.out, dpi=110)


def load_case(d, net):
    m = json.loads((Path(d) / "manifest.json").read_text())
    bx, by = m["solved_um"][:2]
    T = m["tile_um"]
    pts = []
    for line in (Path(d) / f"ir_{net}.rpt").read_text().splitlines()[1:]:
        c = line.split(",")
        if len(c) < 6:
            continue
        nm = c[0].strip()
        if not nm.startswith("T_"):
            continue
        _, i, j = nm.split("_")
        v = float(c[5])
        dv = (VDD - v if net == "VDD" else v) * 1000
        pts.append((bx + int(i) * T, by + int(j) * T, dv))
    return m, pts


def ir(a):
    pm = json.loads(Path(a.power).read_text())
    W, H = 25.19424, 18.3168
    cases = [load_case(d, a.net) for d in a.case]
    vmax = a.vmax or max(max(p[2] for p in pts) for _, pts in cases)
    fig, ax = plt.subplots(figsize=(10, 7.6), dpi=110)
    cmap = plt.get_cmap("inferno")
    norm = matplotlib.colors.Normalize(vmin=0, vmax=vmax)
    for k, (m, pts) in enumerate(cases):
        T = m["tile_um"]
        x0, y0, x1, y1 = m["inner_um"]
        arr = np.array(pts)
        if m["guard_um"] > 0:      # windows: inner area only
            sel = (arr[:, 0] + T / 2 >= x0) & (arr[:, 0] + T / 2 <= x1) & (arr[:, 1] + T / 2 >= y0) & (arr[:, 1] + T / 2 <= y1)
            arr = arr[sel]
        nx = int(round((arr[:, 0].max() - arr[:, 0].min()) / T)) + 1
        ny = int(round((arr[:, 1].max() - arr[:, 1].min()) / T)) + 1
        img = np.full((ny, nx), np.nan)
        ox, oy = arr[:, 0].min(), arr[:, 1].min()
        for x, y, v in arr:
            img[int(round((y - oy) / T)), int(round((x - ox) / T))] = v
        ax.imshow(img, origin="lower", cmap=cmap, norm=norm, interpolation="nearest",
                  extent=(ox / 1000, (ox + nx * T) / 1000, oy / 1000, (oy + ny * T) / 1000))
        if m["guard_um"] > 0:
            ax.add_patch(Rectangle((x0 / 1000, y0 / 1000), (x1 - x0) / 1000, (y1 - y0) / 1000, fill=False, ec="cyan", lw=1.0))
        i = int(np.argmax(arr[:, 2]))
        wx, wy, wv = arr[i]
        ax.plot((wx + T / 2) / 1000, (wy + T / 2) / 1000, "x", color="cyan", ms=6, mew=1.5)
        ax.annotate(f"{wv:.1f} mV", ((wx + T / 2) / 1000, (wy + T / 2) / 1000), fontsize=6, color="cyan",
                    xytext=(4, 4), textcoords="offset points")
    outlines(ax, pm)
    fig.colorbar(plt.cm.ScalarMappable(norm=norm, cmap=cmap), ax=ax, fraction=0.03,
                 label=f"{a.net} {'drop' if a.net == 'VDD' else 'rise'} (mV)")
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_xlabel("x (mm)"); ax.set_ylabel("y (mm)")
    ax.set_title(a.title or f"B2r2 {a.net} IR (PDNSim, estimated power); x = worst node per case; cyan = exact-grid windows", fontsize=8)
    fig.tight_layout(); fig.savefig(a.out, dpi=110)


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["power", "ir"])
    p.add_argument("--power", required=True)
    p.add_argument("--case", action="append", default=[])
    p.add_argument("--net", default="VDD")
    p.add_argument("--vmax", type=float)
    p.add_argument("--title")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    (power if a.mode == "power" else ir)(a)
