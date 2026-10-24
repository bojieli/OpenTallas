#!/usr/bin/env python3
"""kits_repin floorplan review render (owner order 10-24 08:05 "review before you route").

    python3 render_kit.py KITDIR OUT.png [--placed placed.csv]      (placed.csv from cores/svc/dump_placed.py)

Draws the kit's outline + core area, every plan pin (colour = bus group, labels per group), the clock / reset pins,
macro sites with their row halo, the M5 PDN stripe pitch over the core, and (with --placed) the placed std cells
(density), flops and the face flops.  Lower panels: pins per um along each face (2-um bins) against the face track
capacity of the pin layers used (M4 E/W every 2nd 0.048 track = 10.4 /um; N/S M3 every 2nd 0.036 + M5 every 2nd 0.048 = 24.3 /um).
Writes OUT.png and OUT.json (per-face counts, max density, clock pin, macro clearances to each face).
"""
import argparse
import colorsys
import csv
import json
import re
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402

M = 4.32


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("kit")
    ap.add_argument("out")
    ap.add_argument("--placed")
    a = ap.parse_args()
    K = Path(a.kit)
    fz = json.loads((K / "freeze.json").read_text())
    W, H = fz["outline_um"]
    pins = json.loads((K / "pins.json").read_text())
    cfg = (K / "config.mk").read_text()
    halo = re.search(r"MACRO_ROWS_HALO_X = ([\d.]+)", cfg)
    halo = float(halo.group(1)) if halo else 2.0
    macros = []
    for mline in fz.get("macros", []):
        master, x, y, o = mline.split()
        lef = (K / "macros" / f"{master}.lef").read_text()
        sz = re.search(r"SIZE ([\d.]+) BY ([\d.]+)", lef)
        macros.append((master, float(x), float(y), float(sz.group(1)), float(sz.group(2))))
    groups = sorted({p["bus"] for p in pins})
    col = {g: colorsys.hsv_to_rgb((i * 0.618) % 1, 0.85, 0.85) for i, g in enumerate(groups)}
    fig = plt.figure(figsize=(14, 14 * H / W * 0.75 + 4), dpi=120)
    gs = fig.add_gridspec(2, 4, height_ratios=[3.2, 1])
    ax = fig.add_subplot(gs[0, :])
    st = dict(kit=fz["kit"], kit_hash=fz["kit_hash"], outline_um=[W, H], pins=len(pins), faces={}, macros=[])
    if a.placed:
        rows = list(csv.DictReader(open(a.placed)))
        std = [r for r in rows if r["kind"] in ("std", "ff", "buf")]
        nb = int(np.ceil(W / 5)), int(np.ceil(H / 5))
        den = np.zeros(nb)
        for r in std:
            den[min(nb[0] - 1, int(float(r["x"]) / 5)), min(nb[1] - 1, int(float(r["y"]) / 5))] += \
                float(r["w"]) * float(r["h"]) / 25.0
        ax.imshow(den.T, origin="lower", extent=(0, nb[0] * 5, 0, nb[1] * 5), cmap="Greys", vmin=0, vmax=1.0, alpha=0.8)
        ff = [r for r in std if r["kind"] == "ff"]
        ax.scatter([float(r["x"]) for r in ff], [float(r["y"]) for r in ff], s=0.2, color="tab:green", alpha=0.3,
                   label=f"flops {len(ff)}")
        st["placed"] = dict(cells=len(std), flops=len(ff), bins5_over_0p8=int((den > 0.8).sum()),
                            max_bin=round(float(den.max()), 2))
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1.2))
    ax.add_patch(plt.Rectangle((M, M), W - 2 * M, H - 2 * M, fill=False, lw=0.6, ls="--", ec="grey"))
    # M5 PDN stripes (pitch 4.32, offset 2.064 from the core origin; VSS/VDD pair) over the core only
    for k in range(int((W - 2 * M) / 4.32) + 1):
        x = M + 2.004 + k * 4.32
        if x < W - M:
            ax.plot([x, x], [M, H - M], lw=0.25, color="orange", alpha=0.5)
    for master, x, y, w, h in macros:
        ax.add_patch(plt.Rectangle((x - halo, y - halo), w + 2 * halo, h + 2 * halo, fill=True, fc="lightblue",
                                   alpha=0.3, ec="tab:blue", ls=":"))
        ax.add_patch(plt.Rectangle((x, y), w, h, fill=False, ec="tab:blue", lw=1.5))
        ax.text(x + 2, y + h / 2, f"{master}\n({x:g}, {y:g}) halo {halo:g}", fontsize=7, color="tab:blue")
        st["macros"].append(dict(master=master, at=[x, y], size=[w, h], row_halo=halo,
                                 clear_um=dict(W=round(x, 2), E=round(W - x - w, 2), S=round(y, 2), N=round(H - y - h, 2))))
    byg = defaultdict(list)
    for p in pins:
        byg[(p["bus"], p["face"])].append(p)
    for (g, f), ps in byg.items():
        xs, ys = [p["x"] for p in ps], [p["y"] for p in ps]
        ax.scatter(xs, ys, s=4, color=col[g], marker="s")
        cx, cy = np.mean(xs), np.mean(ys)
        off = {"N": (0, 4), "S": (0, -6), "E": (3, 0), "W": (-3, 0)}[f]
        ax.text(cx + off[0], cy + off[1], f"{g}[{len(ps)}]", fontsize=6, color=col[g],
                ha={"E": "left", "W": "right"}.get(f, "center"), va="center",
                rotation=90 if f in "NS" else 0)
    for p in pins:
        if re.match(r"^(clk|ck)$", p["bus"]):
            ax.scatter([p["x"]], [p["y"]], s=160, marker="*", color="red", zorder=5, label=f"clock {p['bus']}")
            st["clock_pin"] = dict(name=p["bus"], x=p["x"], y=p["y"], face=p["face"], layer=p["layer"])
        if re.match(r"^(rst_n|rst)$", p["bus"]):
            ax.scatter([p["x"]], [p["y"]], s=80, marker="D", color="black", zorder=5, label=f"reset {p['bus']}")
    ax.set_xlim(-14, W + 14)
    ax.set_ylim(-10, H + 10)
    ax.set_aspect("equal")
    ax.legend(fontsize=7, loc="center")
    ax.set_title(f"{fz['kit']} {W:g}x{H:g}: {len(pins)} plan pins ({fz['pins_file']}), kit {fz['kit_hash']}"
                 + (" + placed" if a.placed else ""), fontsize=9)
    for i, f in enumerate("NSWE"):
        axf = fig.add_subplot(gs[1, i])
        ps = [p for p in pins if p["face"] == f]
        L = W if f in "NS" else H
        c = [p["x"] if f in "NS" else p["y"] for p in ps]
        bins = np.arange(0, L + 2, 2.0)
        hst, _ = np.histogram(c, bins=bins)
        axf.bar(bins[:-1], hst / 2.0, width=2.0, color="tab:purple")
        cap = 24.3 if f in "NS" else 10.42   # N/S: M3 every 2nd 0.036 (13.9) + M5 every 2nd 0.048 (10.4); E/W: M4 every 2nd (10.4)
        axf.axhline(cap, color="red", lw=0.8, ls="--")
        axf.set_title(f"face {f}: {len(ps)} pins, max {hst.max() / 2.0 if len(ps) else 0:.1f}/um (cap {cap})", fontsize=8)
        axf.set_ylim(0, 26)
        axf.tick_params(labelsize=6)
        lay = defaultdict(int)
        for p in ps:
            lay[p["layer"]] += 1
        st["faces"][f] = dict(pins=len(ps), max_per_um=float(hst.max() / 2.0) if len(ps) else 0.0,
                              mean_per_um=round(len(ps) / L, 2), layers=dict(lay),
                              span=[round(min(c), 2), round(max(c), 2)] if c else None,
                              groups=sorted({p["bus"] for p in ps}))
    fig.tight_layout()
    fig.savefig(a.out)
    Path(a.out + ".json").write_text(json.dumps(st, indent=1) + "\n")
    print(json.dumps({k: v for k, v in st.items() if k != "faces"}),
          {f: (v["pins"], v["max_per_um"]) for f, v in st["faces"].items()})


if __name__ == "__main__":
    main()
