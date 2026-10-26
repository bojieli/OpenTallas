#!/usr/bin/env python3
"""Visual review renders of a trial die (lane TRIAL-HBM; owner order 08:05: render, look, write what looks wrong).

    render.py PLAN.json --out DIR [--run FABRIC_RUN_DIR] [--htree clock_htree.json] [--bin 250]
      DIR/floorplan.png   partitions by role, hard cores, IO / PHY keep-outs, lane bundles (line width ~ bits),
                          ft stations, the H-tree, the die PG/root
      DIR/congestion.png  per layer M4..M9 raw track usage per bin from the fabric GRT guides (+ hot bins listed)
      DIR/hops.png        hop length map: every fabric hop > 700 um drawn driver->receiver, coloured by length
      DIR/slack.png       (if RUN/sta_*_SS_max.end) worst SS setup slack per receiving partition
"""
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import LineCollection  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402
import numpy as np  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "die_plan"))
sys.path.insert(0, str(HERE))
import check  # noqa: E402
import schema as S  # noqa: E402
import fabric  # noqa: E402
import fabric_report  # noqa: E402

ROLE_COL = [("sm", "#9ecae1"), ("su", "#fdd0a2"), ("hub", "#fc9272"), ("b0", "#c7e9c0"), ("b1", "#a1d99b"),
            ("sp", "#e5e5e5"), ("vs", "#dadaeb"), ("root", "#bcbddc"), ("io", "#fee391"), ("PHY", "#fa9fb5"),
            ("mc", "#f0f0f0")]


def role_color(tn):
    t = tn.replace("q_", "")
    for k, c in ROLE_COL:
        if t.startswith(k) or k in tn:
            return c
    return "#ffffff"


def base(ax, P, names=True, fs=5):
    for n, p in P.parts.items():
        x0, y0, x1, y1 = P.rect(n)
        ax.add_patch(Rectangle((x0 / 1e3, y0 / 1e3), (x1 - x0) / 1e3, (y1 - y0) / 1e3, fc=role_color(p["type"]),
                               ec="k", lw=0.4))
        if names:
            ax.text((x0 + x1) / 2e3, (y0 + y1) / 2e3, n.replace("NW_", "").replace("NE_", "") +
                    ("'" if n.startswith("NE_") else ""), ha="center", va="center", fontsize=fs)
    ax.set_xlim(0, P.W / 1e3)
    ax.set_ylim(0, P.H / 1e3)
    ax.set_aspect("equal")
    ax.set_xlabel("x mm")
    ax.set_ylabel("y mm")


def floorplan(P, plan_dir, out, htree=None):
    fig, ax = plt.subplots(figsize=(16, 12))
    base(ax, P, fs=6)
    for L, x0, y0, x1, y1, why in fabric.blockages(P, plan_dir, None):
        if L != "M4" or why == "pg":
            continue
        kind = why.split()[0]
        ax.add_patch(Rectangle((x0 / 1e3, y0 / 1e3), (x1 - x0) / 1e3, (y1 - y0) / 1e3,
                               fc={"core": "#77777755", "leaf": "#aaaaaa44", "keepout": "#d6272855"}[kind],
                               ec="none", hatch="////" if kind == "keepout" else None))
    segs, lw, cols = [], [], []
    for lid in P.lanes:
        pts, regs, xs = check.lane_geometry(P, lid)
        bits = S.port_pins_count(P.ports[P.lanes[lid]["ports"][0]])
        for a, b in zip(pts, pts[1:]):
            segs.append([(a[0] / 1e3, a[1] / 1e3), (b[0] / 1e3, b[1] / 1e3)])
            lw.append(0.3 + 3.0 * min(1.0, bits / 4000))
            cols.append("#08519c" if bits < 2000 else "#cb181d")
    ax.add_collection(LineCollection(segs, linewidths=lw, colors=cols, alpha=0.55))
    if htree:
        ht = json.loads(Path(htree).read_text())
        hs = [[(s["xy"][0] / 1e3, s["xy"][1] / 1e3), (s["xy"][2] / 1e3, s["xy"][3] / 1e3)] for s in ht["segments"]]
        ax.add_collection(LineCollection(hs, linewidths=0.8, colors="#ff7f00", linestyles="dashed", alpha=0.9))
        lv = np.array(ht["leaves"]) / 1e3
        ax.plot(lv[:, 0], lv[:, 1], "^", ms=2.5, color="#ff7f00")
        r = ht["root_um"]
        ax.plot(r[0] / 1e3, r[1] / 1e3, "*", ms=14, color="#ff7f00")
    ax.set_title(f"{P.name}: floorplan, lane bundles (blue < 2k bits, red >= 2k; width ~ bits), hard cores (grey), "
                 "IO/PHY keep-outs (red hatch), H-tree (orange)")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)


def congestion(P, run, out, B):
    W, H = P.W, P.H
    nx, ny = int(W // B) + 1, int(H // B) + 1
    g = {L: np.zeros((ny, nx)) for L in fabric_report.DIRS}
    for net, boxes in fabric_report.read_guides(Path(run) / "fabric.guide"):
        for x0, y0, x1, y1, L in boxes:
            if L not in g:
                continue
            if fabric_report.DIRS[L] == "H":
                if x1 - x0 <= fabric_report.GC + 1e-3:
                    continue
                j = min(int(((y0 + y1) / 2) // B), ny - 1)
                x = x0
                while x < x1 - 1e-6:
                    i = min(int(x // B), nx - 1)
                    e = min(x1, (i + 1) * B)
                    g[L][j, i] += e - x
                    x = e
            else:
                if y1 - y0 <= fabric_report.GC + 1e-3:
                    continue
                i = min(int(((x0 + x1) / 2) // B), nx - 1)
                y = y0
                while y < y1 - 1e-6:
                    j = min(int(y // B), ny - 1)
                    e = min(y1, (j + 1) * B)
                    g[L][j, i] += e - y
                    y = e
    fig, axs = plt.subplots(2, 3, figsize=(21, 10.5))
    hot = {}
    for ax, L in zip(axs.flat, ["M4", "M5", "M6", "M7", "M8", "M9"]):
        cap = B / P.layers[L]["pitch_um"]
        u = g[L] / B / cap
        hot[L] = float(u.max())
        im = ax.imshow(u, origin="lower", extent=(0, nx * B / 1e3, 0, ny * B / 1e3), cmap="magma_r", vmin=0,
                       vmax=0.8)
        for n in P.parts:
            x0, y0, x1, y1 = P.rect(n)
            ax.add_patch(Rectangle((x0 / 1e3, y0 / 1e3), (x1 - x0) / 1e3, (y1 - y0) / 1e3, fc="none", ec="#1f77b4",
                                   lw=0.3))
        ax.set_xlim(0, W / 1e3)
        ax.set_ylim(0, H / 1e3)
        ax.set_title(f"{L} ({fabric_report.DIRS[L]}) raw track usage per {B:g} um bin, max {u.max():.2f}")
        plt.colorbar(im, ax=ax, fraction=0.03)
    fig.suptitle(f"{P.name}: die fabric GRT demand (all lane hops), raw tracks (before PG / H-tree / own-logic derate)")
    fig.tight_layout()
    fig.savefig(out, dpi=90)
    plt.close(fig)
    return hot


def hops(P, run, out, thr=700.0):
    cells = {}
    # positions are not in nets.tsv: rebuild from the plan (cheap)
    c, nets = fabric.build(P, None)
    segs, cols = [], []
    for nm, d, r, m in nets:
        (xa, ya, _, _), (xb, yb, _, _) = c[d], c[r]
        L = abs(xa - xb) + abs(ya - yb)
        if L > thr:
            segs.append([(xa / 1e3, ya / 1e3), (xb / 1e3, yb / 1e3)])
            cols.append(L)
    fig, ax = plt.subplots(figsize=(16, 12))
    base(ax, P, fs=6)
    lc = LineCollection(segs, array=np.array(cols), cmap="plasma", linewidths=0.25, alpha=0.6)
    lc.set_clim(thr, 960)
    ax.add_collection(lc)
    plt.colorbar(lc, ax=ax, fraction=0.03, label="hop um (driver -> receiver, Manhattan)")
    ax.set_title(f"{P.name}: fabric hops > {thr:g} um ({len(segs)} of {len(nets)} hop nets; reach 1000, 0.9 margin 900)")
    fig.tight_layout()
    fig.savefig(out, dpi=110)
    plt.close(fig)
    del cells


def slack(P, run, out):
    run = Path(run)
    rows = {}
    for f in sorted(run.glob("sta_*_SS_max.end")) + sorted(run.glob("sta_*_FF_min.end")):
        worst = defaultdict(lambda: 1e9)
        for m in re.finditer(r"^(\S+?)__\S+/D \(\S+\)\s+-?[\d.]+\s+-?[\d.]+\s+(-?[\d.]+)", f.read_text(), re.M):
            worst[m.group(1)] = min(worst[m.group(1)], float(m.group(2)))
        rows[f.stem] = worst
    if not rows:
        return None
    nr = (len(rows) + 1) // 2
    fig, axs = plt.subplots(nr, 2, figsize=(22, 8.5 * nr))
    axs = np.atleast_1d(axs).flatten()
    for ax, (k, worst) in zip(axs, rows.items()):
        base(ax, P, names=False)
        vals = [v for v in worst.values() if v < 1e8]
        lo = min(vals) if vals else -1
        for n in P.parts:
            v = worst.get(n)
            if v is None or v > 1e8:
                continue
            x0, y0, x1, y1 = P.rect(n)
            col = plt.cm.RdYlGn(0.5 + 0.5 * max(-1, min(1, v / max(1, abs(lo)))))
            ax.add_patch(Rectangle((x0 / 1e3, y0 / 1e3), (x1 - x0) / 1e3, (y1 - y0) / 1e3, fc=col, ec="k", lw=0.4))
            ax.text((x0 + x1) / 2e3, (y0 + y1) / 2e3, f"{n}\n{v:.0f}", ha="center", va="center", fontsize=6)
        ax.set_title(f"{k}: worst slack (ps) per receiving partition")
    fig.tight_layout()
    fig.savefig(out, dpi=100)
    plt.close(fig)
    return {k: dict(sorted(((n, v) for n, v in w.items()), key=lambda kv: kv[1])[:8]) for k, w in rows.items()}


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan")
    ap.add_argument("--out", required=True)
    ap.add_argument("--run")
    ap.add_argument("--slack-run", action="append", default=[])
    ap.add_argument("--htree")
    ap.add_argument("--bin", type=float, default=250.0)
    a = ap.parse_args(argv)
    P = S.Plan(S.load(a.plan))
    plan_dir = Path(a.plan).resolve().parent
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    floorplan(P, plan_dir, out / "floorplan.png", a.htree)
    res = {}
    if a.run:
        res["congestion_max"] = congestion(P, a.run, out / "congestion.png", a.bin)
        hops(P, a.run, out / "hops.png")
    for i, r in enumerate(a.slack_run):
        res[f"slack_{Path(r).name}"] = slack(P, r, out / f"slack_{Path(r).name}.png")
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    sys.exit(main())
