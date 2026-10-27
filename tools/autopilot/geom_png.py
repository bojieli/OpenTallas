#!/usr/bin/env python3
"""geom_png.py -- AUTO-GEOM image (GEOM-AUTO-2 2026-10-27): placement of a geom_dump.tcl dump with the rule results.

    geom_png.py DUMP.tsv auto_geom.json OUT.png [--cong cong.rpt]

Draws: die outline, macros (grey, hatched = obstructed layers), std-cell density (heat), flops (dots), top pins
coloured by layer, clock root ports (stars) and pre-placed clock cells, the farthest clock sink, the worst channel /
column demand window (orange box), GRT overflow gcells when the probe ended with overflow (red), and the verdict with
its FAIL / WARN reasons in the title.  Read-only; reviewers still Read the PNG for any visual verdict.
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import geom_rules as GR  # noqa: E402


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("dump")
    ap.add_argument("json")
    ap.add_argument("png")
    ap.add_argument("--cong")
    a = ap.parse_args(argv)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np
    from matplotlib.patches import Rectangle
    res = json.load(open(a.json))
    m = res["metrics"]
    die, cells, pins, _ = GR.load(a.dump)
    X0, Y0, X1, Y1 = die
    W, H = X1 - X0, Y1 - Y0
    s = 9.0 / max(W, H)
    fig, ax = plt.subplots(figsize=(max(4.0, W * s) + 1.5, max(4.0, H * s) + 1.6), dpi=130)
    ax.add_patch(Rectangle((X0, Y0), W, H, fill=False, lw=1.0, ec="k"))
    std = [c for c in cells.values() if c[0] in "SBKL"]
    if std:
        bw = max(max(W, H) / 120.0, 1.0)
        xs = np.array([(c[2] + c[4]) / 2 for c in std]); ys = np.array([(c[3] + c[5]) / 2 for c in std])
        ar = np.array([(c[4] - c[2]) * (c[5] - c[3]) for c in std])
        hb, xe, ye = np.histogram2d(xs, ys, bins=[max(1, int(W / bw)), max(1, int(H / bw))],
                                    range=[[X0, X1], [Y0, Y1]], weights=ar)
        dens = hb.T / (bw * bw)
        ax.imshow(np.ma.masked_where(dens <= 0, dens), origin="lower", extent=[X0, X1, Y0, Y1], cmap="Blues",
                  vmin=0, vmax=0.8, alpha=0.85, interpolation="nearest", aspect="equal")
        ff = [c for c in std if c[0] == "S"]
        if ff:
            step = max(1, len(ff) // 40000)
            ax.scatter([(c[2] + c[4]) / 2 for c in ff[::step]], [(c[3] + c[5]) / 2 for c in ff[::step]], s=0.15,
                       c="navy", lw=0, alpha=0.5)
    for c in cells.values():
        if c[0] == "M":
            ax.add_patch(Rectangle((c[2], c[3]), c[4] - c[2], c[5] - c[3], fc="0.75", ec="0.3", lw=0.6, hatch="//",
                                   alpha=0.9))
    cols = {"M2": "tab:olive", "M3": "tab:purple", "M4": "tab:green", "M5": "tab:red", "M6": "tab:cyan",
            "M7": "tab:brown"}
    for lay in sorted({p["layer"] for p in pins}):
        pp = [p for p in pins if p["layer"] == lay and p["sig"] not in ("POWER", "GROUND")]
        if pp:
            ax.scatter([p["x"] for p in pp], [p["y"] for p in pp], s=2, marker="s", c=cols.get(lay, "k"), lw=0,
                       label=f"pins {lay} ({len(pp)})")
    ts = m.get("tap_sinks") or {}
    for p in pins:
        if ts.get(p["name"], 0) > 0:
            ax.scatter([p["x"]], [p["y"]], s=140, marker="*", c="gold", ec="k", lw=0.6, zorder=5)
            ax.annotate(f"{p['name']} ({ts[p['name']]})", (p["x"], p["y"]), fontsize=6, xytext=(4, 4),
                        textcoords="offset points")
    if m.get("clock_reach_far"):
        fx, fy = m["clock_reach_far"]
        ax.scatter([fx], [fy], s=40, marker="x", c="m", zorder=5, label=f"farthest clock sink {m.get('clock_reach_max')} um")
    for key, d in (("channel_h_at", "H"), ("channel_v_at", "V")):
        at = m.get(key)
        if at:
            a0, a1, c = at
            r = (Rectangle((c - 2.5, a0), 5, a1 - a0) if d == "H" else Rectangle((a0, c - 2.5), a1 - a0, 5))
            r.set(fill=False, ec="darkorange", lw=1.5, zorder=6)
            ax.add_patch(r)
            ax.annotate(f"{d} {m.get(key.replace('_at', '_max'))}", (r.get_x(), r.get_y()), fontsize=6, color="darkorange")
    if m.get("col_v_at"):
        x, c = m["col_v_at"]
        ax.add_patch(Rectangle((x, c - 2.5), GR.DEMAND_WIN, 5, fill=False, ec="orangered", lw=1.5, zorder=6))
        ax.annotate(f"col V {m.get('col_v_max')}", (x, c + 3), fontsize=6, color="orangered")
    if a.cong and (m.get("grt_overflow") or 0) > 0 and Path(a.cong).is_file():
        bx = re.findall(r"bbox = \(([\d.]+), ([\d.]+)\) - \(([\d.]+), ([\d.]+)\)", Path(a.cong).read_text(errors="replace"))
        for b in bx[:20000]:
            x0, y0, x1, y1 = map(float, b)
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="red", ec="none", alpha=0.5, zorder=4))
    ax.set_xlim(X0 - 0.02 * W, X1 + 0.02 * W)
    ax.set_ylim(Y0 - 0.02 * H, Y1 + 0.02 * H)
    ax.set_aspect("equal")
    bad = [r["rule"] for r in res["rules"] if r["status"] in ("FAIL", "NA")]
    warn = [r["rule"] for r in res["rules"] if r["status"] == "WARN"]
    t = (f"AUTO-GEOM {res['verdict']}  {W:.1f}x{H:.1f}  fill {m.get('fill_of_free')}  GRT ov {m.get('grt_overflow')}\n"
         f"FAIL/NA: {', '.join(bad) or '-'}" + (f"   WARN: {', '.join(warn)}" if warn else ""))
    ax.set_title(t, fontsize=8, color="darkred" if res["verdict"] == "FAIL" else "darkgreen")
    ax.legend(fontsize=5, loc="upper left", bbox_to_anchor=(1.0, 1.0), markerscale=3)
    fig.tight_layout()
    fig.savefig(a.png)
    print("AP_AUTO_GEOM_PNG", a.png)


if __name__ == "__main__":
    main()
