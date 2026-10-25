#!/usr/bin/env python3
"""Render a PROTO skeleton prototype (proto_sweep.py) in the GEOM-REVIEW review.png style:
outline, hard-core / leaf blockages (grey), pin boundary flops (in green / out blue), ft station flops (orange),
repair buffers (black dots), clock / reset tap pins (red stars), GRT overflow gcells (red, alpha by count),
title = type, GRT overflow, skeleton TT setup / FF hold WNS, class.

    proto_render.py PROBE_DIR [OUT.png]
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def render(d, out=None):
    d = Path(d)
    meta = json.loads((d / ("proto.json" if (d / "proto.json").exists() else "probe.json")).read_text())
    w, h = meta["outline_um"]
    tcl = (d / "probe.tcl").read_text()
    blk = [tuple(map(float, m.groups())) for m in
           re.finditer(r"create_blockage -region \{([\d.e-]+) ([\d.e-]+) ([\d.e-]+) ([\d.e-]+)\}", tcl)]
    taps = [(m.group(1), float(m.group(2)), float(m.group(3))) for m in
            re.finditer(r"place_inst -name tap_(\S+) -location \{([\d.]+) ([\d.]+)\}", tcl)]
    pts = {"in": [], "out": [], "st": [], "buf": []}
    if (d / "insts.tsv").exists():
        for ln in (d / "insts.tsv").read_text().splitlines():
            p = ln.split("\t")
            if len(p) < 4:
                continue
            n, m, x, y = p[0], p[1], float(p[2]), float(p[3])
            if n.startswith("st_"):
                pts["st"].append((x, y))
            elif n.startswith("bf_"):
                pts["in" if "nq_" not in n else "in"].append((x, y))
            elif re.match(r"^(BUF|INV|HB)", m) and not n.startswith("tap_"):
                pts["buf"].append((x, y))
    planned = not (d / "insts.tsv").exists()
    if planned:
        # Before admission, render the exact sites that the skeleton will place.
        # Keep the title explicit: these are planned sites, not routed evidence.
        for n, x, y in re.findall(r"place_inst -name (\S+) -location \{([\d.e-]+) ([\d.e-]+)\}", tcl):
            if n.startswith("st_"):
                pts["st"].append((float(x), float(y)))
            elif n.startswith("bf_"):
                pts["in"].append((float(x), float(y)))
    # boundary flops: classify in/out from probe.v
    if not planned and (d / "probe.v").exists() and pts["in"]:
        outs = set(re.findall(r"DFFHQNx1_ASAP7_75t_R (bf_\S+) \(.*\.D\(nd_", (d / "probe.v").read_text()))
        pos = {}
        for ln in (d / "insts.tsv").read_text().splitlines():
            p = ln.split("\t")
            if len(p) >= 4 and p[0].startswith("bf_"):
                pos[p[0]] = (float(p[2]), float(p[3]))
        pts["in"] = [v for k, v in pos.items() if k not in outs]
        pts["out"] = [v for k, v in pos.items() if k in outs]
    hot = Counter()
    if (d / "grt_congestion.rpt").exists():
        for m in re.finditer(r"bbox = \( *([\d.]+), *([\d.]+) *\) - \( *([\d.]+), *([\d.]+) *\)",
                             (d / "grt_congestion.rpt").read_text(errors="replace")):
            hot[tuple(float(m.group(i)) for i in range(1, 5))] += 1
    sc = 9.0 / max(w, h)
    fig, ax = plt.subplots(figsize=(max(4.0, w * sc) + 1.5, max(4.0, h * sc) + 1.2), dpi=110)
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.2, ec="k"))
    for x0, y0, x1, y1 in blk:
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="0.75", ec="0.4", lw=0.5))
    mx = max(hot.values()) if hot else 1
    for (x0, y0, x1, y1), c in hot.items():
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="red", ec="none", alpha=0.25 + 0.6 * c / mx))
    for k, col, s in (("in", "#1a9850", 0.6), ("out", "#2166ac", 0.6), ("st", "#f46d43", 0.6), ("buf", "k", 0.3)):
        if pts[k]:
            xs, ys = zip(*pts[k])
            ax.scatter(xs, ys, s=s, c=col, marker=".", linewidths=0, label=f"{k} {len(pts[k])}")
    for n, x, y in taps:
        ax.scatter([x], [y], s=40, c="red", marker="*", zorder=5)
    s = meta.get("sta", {})
    cl = meta.get("classify", {})
    ax.set_title(f"{'PLANNED SITES | ' if planned else ''}{meta['die']} {meta['type']} {w:.0f}x{h:.0f} um | GRT ov {meta.get('total_overflow')} "
                 f"({meta.get('hot_gcells', 0)} gc) | TT setup {s.get('tt_setup_wns')} / FF hold "
                 f"{s.get('ff_hold_wns')} ps | {cl.get('cls', '')}", fontsize=8)
    ax.set_xlim(-0.02 * w, 1.02 * w)
    ax.set_ylim(-0.02 * h, 1.02 * h)
    ax.set_aspect("equal")
    ax.legend(loc="upper right", fontsize=6, markerscale=8, framealpha=0.7)
    ax.tick_params(labelsize=6)
    fig.tight_layout()
    out = Path(out) if out else d / "review.png"
    fig.savefig(out)
    plt.close(fig)
    return out


if __name__ == "__main__":
    print(render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
