#!/usr/bin/env python3
"""HBM-CONS-1 visual check: render a dumped core (dump_placed.py CSV) + optional GRT congestion / DRC report.

    python3 -I vk_render.py CSV OUT.png --die W H [--cong congestion.rpt] [--drc drc.rpt] [--title T]

Panels: (1) cell density (5 um bins) + macros + pins; (2) pin -> landing-flop flight lines (sampled) + clock buffers;
(3) GRT congestion / DRC boxes by layer.  Prints SMELL metrics (max local density, pin clumps per 20 um of edge,
pin->flop distance, macro channel widths, clock buffer spread) for the post.
"""
import argparse, csv, math, re, collections, json


def parse_boxes(path):
    """DRC-viewer style reports (ORFS congestion.rpt / 5_route_drc.rpt): 'bbox = ( x0, y0 ) - ( x1, y1 ) on Layer M3'"""
    out = []
    if not path:
        return out
    try:
        txt = open(path).read()
    except OSError:
        return out
    for m in re.finditer(r"bbox\s*=\s*\(\s*([-\d.]+),\s*([-\d.]+)\s*\)\s*-\s*\(\s*([-\d.]+),\s*([-\d.]+)\s*\)\s*on Layer\s*(\S+)", txt):
        out.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4)), m.group(5)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv")
    ap.add_argument("out")
    ap.add_argument("--die", nargs=2, type=float, required=True)
    ap.add_argument("--cong")
    ap.add_argument("--drc")
    ap.add_argument("--title", default="")
    ap.add_argument("--bin", type=float, default=5.0)
    a = ap.parse_args()
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.patches import Rectangle
    import numpy as np

    W, H = a.die
    rows = list(csv.DictReader(open(a.csv)))
    cells = [r for r in rows if r["kind"] in ("std", "ff", "buf", "tap")]
    macros = [r for r in rows if r["kind"] == "macro"]
    pins = [r for r in rows if r["kind"] == "pin"]
    pos = {r["name"]: (float(r["x"]) + float(r["w"]) / 2, float(r["y"]) + float(r["h"]) / 2) for r in cells}
    nb_x, nb_y = max(1, int(math.ceil(W / a.bin))), max(1, int(math.ceil(H / a.bin)))
    dens = np.zeros((nb_y, nb_x))
    for r in cells:
        x, y, w, h = (float(r[k]) for k in ("x", "y", "w", "h"))
        i, j = min(nb_x - 1, max(0, int((x + w / 2) / a.bin))), min(nb_y - 1, max(0, int((y + h / 2) / a.bin)))
        dens[j, i] += w * h
    dens /= a.bin * a.bin
    # macro bins excluded from the density statistic
    mask = np.zeros_like(dens, dtype=bool)
    for m in macros:
        x, y, w, h = (float(m[k]) for k in ("x", "y", "w", "h"))
        mask[int(y / a.bin):int(math.ceil((y + h) / a.bin)), int(x / a.bin):int(math.ceil((x + w) / a.bin))] = True
    free = dens[~mask] if (~mask).any() else dens.ravel()
    smell = {"cells": len(cells), "macros": len(macros), "pins": len(pins),
             "dens_max_5um": round(float(free.max()) if free.size else 0, 3),
             "dens_p99_5um": round(float(np.percentile(free, 99)) if free.size else 0, 3),
             "bins_over_0.7": int((free > 0.7).sum()), "bins_empty_frac": round(float((free < 0.02).mean()) if free.size else 0, 3)}
    # pin clumps: pins per 20 um of each face
    face = collections.Counter()
    for p in pins:
        x, y = float(p["x"]), float(p["y"])
        d = min((x, "W"), (W - x, "E"), (y, "S"), (H - y, "N"))
        coord = y if d[1] in "WE" else x
        face[(d[1], int(coord // 20))] += 1
    smell["pin_max_per20um"] = max(face.values()) if face else 0
    smell["pin_clump_top"] = ["%s@%d-%dum:%d" % (f, b * 20, b * 20 + 20, n) for (f, b), n in face.most_common(4)]
    # pin -> landing flop distance (smell 1/7)
    dist = []
    lines = []
    for p in pins:
        f = p["master"]
        if f and f in pos:
            px, py = float(p["x"]), float(p["y"])
            fx, fy = pos[f]
            dist.append(abs(px - fx) + abs(py - fy))
            lines.append((px, py, fx, fy))
    if dist:
        ds = sorted(dist)
        smell["pin_flop_um_p50"] = round(ds[len(ds) // 2], 1)
        smell["pin_flop_um_p99"] = round(ds[int(len(ds) * 0.99)], 1)
        smell["pin_flop_um_max"] = round(ds[-1], 1)
        smell["pin_flop_over_100um"] = sum(1 for d in ds if d > 100)
    # macro channels (smell 3): min gap between macro pairs that overlap in the other axis, and to the core edge
    gaps = []
    for i, m in enumerate(macros):
        x0, y0 = float(m["x"]), float(m["y"])
        x1, y1 = x0 + float(m["w"]), y0 + float(m["h"])
        gaps.append(("edge", round(min(x0, y0, W - x1, H - y1), 2)))
        for n in macros[i + 1:]:
            a0, b0 = float(n["x"]), float(n["y"])
            a1, b1 = a0 + float(n["w"]), b0 + float(n["h"])
            if min(y1, b1) > max(y0, b0):
                gaps.append(("x", round(max(a0 - x1, x0 - a1), 2)))
            if min(x1, a1) > max(x0, a0):
                gaps.append(("y", round(max(b0 - y1, y0 - b1), 2)))
    pos_gaps = [g for g in gaps if g[1] >= 0]
    smell["macro_min_channel_um"] = min((g[1] for g in pos_gaps if g[0] != "edge"), default=None)
    smell["macro_min_edge_um"] = min((g[1] for g in pos_gaps if g[0] == "edge"), default=None)
    clk = [r for r in cells if re.match(r"(clkbuf|clkload|ot_dtap|cts|CLK)", r["name"]) or r["master"].startswith(("CKINV", "CLKBUF"))]
    if clk:
        cx = [pos[r["name"]][0] for r in clk]
        cy = [pos[r["name"]][1] for r in clk]
        smell["clkbuf"] = len(clk)
        smell["clkbuf_bbox"] = [round(min(cx)), round(min(cy)), round(max(cx)), round(max(cy))]
    cong = parse_boxes(a.cong)
    drc = parse_boxes(a.drc)
    smell["cong_boxes"] = len(cong)
    smell["cong_by_layer"] = dict(collections.Counter(b[4] for b in cong))
    smell["drc_boxes"] = len(drc)

    fig, axs = plt.subplots(1, 3, figsize=(21, 7.5 * max(0.45, min(1.6, H / W))), dpi=110)
    ax = axs[0]
    im = ax.imshow(dens, origin="lower", extent=(0, nb_x * a.bin, 0, nb_y * a.bin), cmap="inferno", vmin=0, vmax=1.0)
    fig.colorbar(im, ax=ax, fraction=0.04, label="cell area / bin area (5 um)")
    ax.set_title("density (max %.2f, p99 %.2f, bins>0.7: %d)" % (smell["dens_max_5um"], smell["dens_p99_5um"], smell["bins_over_0.7"]))
    for axx in axs:
        axx.add_patch(Rectangle((0, 0), W, H, fill=False, ec="k", lw=1))
        for m in macros:
            axx.add_patch(Rectangle((float(m["x"]), float(m["y"])), float(m["w"]), float(m["h"]), fill=False, ec="cyan", lw=1.2))
        axx.set_xlim(-5, W + 5)
        axx.set_ylim(-5, H + 5)
        axx.set_aspect("equal")
    if pins:
        axs[0].scatter([float(p["x"]) for p in pins], [float(p["y"]) for p in pins], s=1, c="lime")
    ax = axs[1]
    step = max(1, len(lines) // 3000)
    for (px, py, fx, fy) in lines[::step]:
        d = abs(px - fx) + abs(py - fy)
        ax.plot([px, fx], [py, fy], lw=0.3, color="red" if d > 100 else ("orange" if d > 40 else "0.6"))
    ff = [pos[r["name"]] for r in cells if r["kind"] == "ff"]
    if ff:
        sstep = max(1, len(ff) // 20000)
        ax.scatter([p[0] for p in ff[::sstep]], [p[1] for p in ff[::sstep]], s=0.2, c="tab:blue", alpha=0.4)
    if clk:
        ax.scatter([pos[r["name"]][0] for r in clk], [pos[r["name"]][1] for r in clk], s=4, c="magenta", marker="x")
    ax.set_title("pin->flop flight lines (red >100 um: %s) + clock bufs (x)" % smell.get("pin_flop_over_100um", 0))
    ax = axs[2]
    cmap = {"M1": "0.5", "M2": "tab:blue", "M3": "tab:green", "M4": "tab:orange", "M5": "tab:red", "M6": "tab:purple", "M7": "k"}
    for (x0, y0, x1, y1, L) in cong:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, color=cmap.get(L, "k"), alpha=0.35, lw=0))
    for (x0, y0, x1, y1, L) in drc:
        ax.add_patch(Rectangle((x0 - 1, y0 - 1), x1 - x0 + 2, y1 - y0 + 2, fill=False, ec="red", lw=1.5))
    ax.set_title("Congestion/DRC not loaded; read actual signoff separately", fontsize=8)
    fig.suptitle(a.title, fontsize=10)
    fig.tight_layout()
    fig.savefig(a.out)
    print("SMELL_METRICS " + json.dumps(smell))


if __name__ == "__main__":
    main()
