#!/usr/bin/env python3
"""QC-A0 10-24: render an A0 v8 kit for the geometry self-review (no P&R): v7 vs v8 side by side --
outline, hard children (+ 8.64-um tap clearance) with their SIGNAL PIN FACE (thick red edge), parent regions (v7 / v8
boxes, hub sub-boxes hd<g>, face boxes f<g>), clock taps (v7 kept = blue dots, moved = magenta with an arrow from the
v7 site, added = green triangles, R4 grid = red stars), the die signal pins, and the cut lines with their ratio
(demand / (0.6 x tracks), uniform model / point model) from tools/qwen_romleaf/a0core/budget/budget.py.
Second figure: vertical-cut ratio profile across the LSL zone and the horizontal cuts, v7 vs v8.

    render_a0c8.py nk|nl BUDGET_DIR OUT_DIR
BUDGET_DIR holds <k>_v7.json, <k>_v7p.json, <k>_v8.json, <k>_v8p.json (budget.py) and <k>_v8_taps_est.json."""
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE / "budget"))
from regions_parse import parse  # noqa: E402

k, bd, od = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3])
od.mkdir(parents=True, exist_ok=True)
B = {l: json.loads((bd / f"{k}_{l}.json").read_text()) for l in ("v7", "v7p", "v8", "v8p")}
EST = json.loads((bd / f"{k}_v8_taps_est.json").read_text())
LSL_FACE_R0 = "E"     # ot_qwen_tile_lsl_fp1: every signal pin on the E face in R0
NODE_FACE_R0 = "E"    # ot_qwen_tile_node: t_d pins on the E face
LEAF_FACE_R0 = "W"    # ot_qwen_tile_romleaf: pins face the central channel (MY leaves at W, R0 leaves at E)
CUTS_V = ["W_col", "M_col", "gap", "E_col"]
CUTS_H = ["H_full.row0", "H_full.row01", "H_full.row1", "H_east.row0", "H_east.row1"]
# x span (um) over which each named vertical cut is searched (budget.py), for the drawn line
CUT_YR = (648.0, 1157.76)


def face_edge(b, face_r0):
    f = face_r0 if b["orient"] == "R0" else {"E": "W", "W": "E"}[face_r0]
    x = b["x"] + (b["w"] if f == "E" else 0)
    return [x, x], [b["y"], b["y"] + b["h"]]


def panel(ax, ver):
    kit = f"physical/ref_tile/qfd_tile_{k}_a0cv{ver}"
    fp = json.loads((ROOT / kit / "floorplan.json").read_text())
    W, H = fp["die"][2], fp["die"][3]
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for b in fp["blocks"]:
        if b.get("kind") != "child":
            continue
        ax.add_patch(Rectangle((b["x"] - 8.64, b["y"] - 8.64), b["w"] + 17.28, b["h"] + 17.28, fc="none", ec="orange",
                               ls=":", lw=0.5))
        lsl = "lsl" in b["master"]
        ax.add_patch(Rectangle((b["x"], b["y"]), b["w"], b["h"], fc="#d8e1ec" if lsl else "#e6e6e6", ec="#456", lw=0.6))
        face = LSL_FACE_R0 if lsl else NODE_FACE_R0 if "node" in b["master"] else None
        if face:
            xs, ys = face_edge(b, face)
            ax.plot(xs, ys, c="red", lw=2.5, solid_capstyle="butt", zorder=3)
            m = re.search(r"g_sl\[(\d)\]", b["inst"])
            ax.text(b["x"] + b["w"] / 2, b["y"] + b["h"] / 2, (f"sl{m.group(1)}\n" if m else "node\n") + b["orient"],
                    ha="center", va="center", fontsize=6)
    reg = ROOT / (f"tools/qwen_romleaf/repack/qfd_tile_{k}_a0v3_regions.tcl" if ver == 7
                  else f"tools/qwen_romleaf/repack/qfd_tile_{k}_a0v8_regions.tcl")
    for g in parse(reg):
        for (x0, y0, x1, y1) in g["boxes"]:
            hub = g["name"].startswith(("hd", "l2c", "hub"))
            fc = "#ffd27f" if hub else "#9fd59f" if g["name"].startswith(("f", "dwr", "der")) else "#c9b8e8"
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc=fc, ec="#555", alpha=0.45 if y0 > 640 else 0.18,
                                   lw=0.4, ls="-" if g["type"] != "EXCLUSIVE" else "--", zorder=2))
            if y0 > 640:
                ax.text((x0 + x1) / 2, (y0 + y1) / 2, g["name"], fontsize=5, ha="center", va="center", zorder=6,
                        rotation=90 if (x1 - x0) < 20 else 0)
    pins = (ROOT / (f"tools/qwen_romleaf/a0core/qfd_tile_{k}_a0c{ver}_pins.tcl")).read_text().splitlines()
    sig = [tuple(map(float, re.search(r"-location \{([\d.]+) ([\d.]+)\}", l).groups())) for l in pins
           if l.startswith("place_pin") and not re.match(r"place_pin -pin_name \{ck", l)]
    ax.scatter([x for x, _ in sig], [y for _, y in sig], s=0.3, c="green", zorder=3)
    taps = json.loads((HERE / f"a0c{ver}_{k}_taps.json").read_text())["taps"]
    for t in taps:
        x, y = t["xy"]
        kd = t["kind"]
        if kd == "grid":
            ax.scatter([x], [y], marker="*", s=90, c="red", zorder=7)
        elif kd == "moved":
            ax.annotate("", (x, y), xytext=tuple(t["v7_xy"]), arrowprops=dict(arrowstyle="->", color="m", lw=0.8), zorder=7)
            ax.scatter([x], [y], s=30, c="m", zorder=7)
        elif kd == "added":
            ax.scatter([x], [y], marker="^", s=40, c="limegreen", ec="k", lw=0.4, zorder=7)
        else:
            ax.scatter([x], [y], s=12, c="blue", alpha=0.8, zorder=7)
        ax.annotate(t["name"].replace("ck_t", ""), (x, y), fontsize=5, xytext=(2, 2), textcoords="offset points", zorder=8)
    lab = "v7" if ver == 7 else "v8"
    S, Sp = B[lab]["summary"], B[lab + "p"]["summary"]
    for c in CUTS_V:
        x = S[c]["x"]
        bad = S[c]["ratio"] > 0.6
        ax.plot([x, x], CUT_YR, c="crimson" if bad else "teal", lw=0.9, ls="--", zorder=5)
        ax.text(x, CUT_YR[1] + 4 + 10 * CUTS_V.index(c), f"{c} {S[c]['ratio']:.2f}/{Sp[c]['ratio']:.2f}", fontsize=5.5,
                color="crimson" if bad else "teal", ha="center")
    for c in CUTS_H:
        y = S[c]["y"]
        x0, x1 = (0, W) if c.startswith("H_full") else (200.4, W)
        bad = S[c]["ratio"] > 0.6
        ax.plot([x0, x1], [y, y], c="crimson" if bad else "teal", lw=0.7, ls=":", zorder=5)
        ax.text(x1 + 2, y, f"{c[2:]} {S[c]['ratio']:.2f}/{Sp[c]['ratio']:.2f}", fontsize=5, va="center",
                color="crimson" if bad else "teal")
    ax.set_xlim(-10, W + 95); ax.set_ylim(-10, H + 50); ax.set_aspect("equal")
    ax.set_title(f"qfd_tile_{k}_a0cv{ver}: {len(taps)} taps; cut ratio uniform/point (red > 0.6)", fontsize=7)
    return W, H


def floorplans():
    fig, axs = plt.subplots(1, 2, figsize=(13, 15))
    for ax, v in zip(axs, (7, 8)):
        panel(ax, v)
    fig.suptitle(f"A0 {k.upper()} v7 -> v8 (F1: per-head hub co-location + E column MY); red edge = signal pin face; "
                 "orange = hub boxes, green = face / writer boxes, purple = ROM-zone boxes; "
                 "taps: blue kept, magenta moved, green ^ added, red * grid", fontsize=8)
    fig.tight_layout()
    p = od / f"qfd_tile_{k}_a0cv8_floorplan.png"
    fig.savefig(p, dpi=150)
    # zoomed LSL / hub zone
    for ax in axs:
        ax.set_ylim(630, 1200); ax.set_xlim(-10, 555)
    fig.set_size_inches(14, 8.5)
    p2 = od / f"qfd_tile_{k}_a0cv8_lslzone.png"
    fig.savefig(p2, dpi=170)
    plt.close(fig)
    return [p, p2]


def cuts():
    fig, axs = plt.subplots(1, 2, figsize=(13, 4.5))
    ax = axs[0]
    for lab, c, ls in (("v7", "crimson", "-"), ("v7p", "crimson", ":"), ("v8", "teal", "-"), ("v8p", "teal", ":")):
        vc = [r for r in B[lab]["vcuts"] if 60 <= r[0] <= 457]
        ax.plot([r[0] for r in vc], [r[1] / (0.6 * r[3]) if r[3] else 0 for r in vc], c=c, ls=ls,
                label=f"{lab} ({'point' if lab.endswith('p') else 'uniform'} model)")
    ax.axhline(1.0, c="k", lw=0.6)
    ax.set_xlabel("x (um), cuts over the LSL zone y >= 648"); ax.set_ylabel("demand / (0.6 x tracks M2-M7)")
    ax.set_title(f"{k.upper()} vertical cuts (> 1 = over the 0.6 budget)", fontsize=8); ax.legend(fontsize=6)
    ax = axs[1]
    names = CUTS_V + CUTS_H + ["H_full.band"]
    xs = range(len(names))
    for i, (lab, c) in enumerate((("v7", "crimson"), ("v8", "teal"))):
        ax.bar([x + 0.2 * (2 * i - 1) for x in xs], [B[lab]["summary"][n]["ratio"] / 0.6 for n in names], width=0.38,
               color=c, label=lab + " uniform")
        ax.scatter([x + 0.2 * (2 * i - 1) for x in xs], [B[lab + "p"]["summary"][n]["ratio"] / 0.6 for n in names],
                   c="k", s=8, zorder=5, label=lab + " point" if i == 0 else None)
    ax.axhline(1.0, c="k", lw=0.6)
    ax.set_xticks(list(xs)); ax.set_xticklabels(names, rotation=60, fontsize=6)
    ax.set_title(f"{k.upper()} named cuts: demand / (0.6 x tracks)", fontsize=8); ax.legend(fontsize=6)
    fig.tight_layout()
    p = od / f"qfd_tile_{k}_a0cv8_cuts.png"
    fig.savefig(p, dpi=150)
    plt.close(fig)
    return [p]


if __name__ == "__main__":
    for p in floorplans() + cuts():
        print(p)
