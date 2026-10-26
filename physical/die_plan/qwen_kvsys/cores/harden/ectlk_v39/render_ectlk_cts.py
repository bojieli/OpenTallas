#!/usr/bin/env python3
"""KV-CORES-PAR 10-24: qkd_ectlk place+CTS review image (centre-fed clock, plan v3.9).
    python3 render_ectlk_cts.py KITDIR placed.csv clk_arrival.csv OUTPNG
Top: placement after CTS (macros, std cells, flops, clock buffers clkbuf*/clkload*, clock / reset pins).
Bottom: per-register clock arrival (TC, placement RC, raw CTS before repair), colour = ps."""
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def main(kd, placed, arr, outp):
    fz = json.load(open(Path(kd) / "freeze.json"))
    W, H = fz["outline_um"]
    rows = list(csv.DictReader(open(placed)))
    pos = {r["name"]: r for r in rows if r["kind"] != "pin"}
    pins = [r for r in rows if r["kind"] == "pin"]
    fig, ax = plt.subplots(2, 1, figsize=(22, 12), dpi=110)
    a = ax[0]
    for r in rows:
        k = r["kind"]
        x, y, w, h = (float(r[c]) for c in ("x", "y", "w", "h"))
        if k == "macro":
            a.add_patch(Rectangle((x, y), w, h, fc="#9ab", ec="k", lw=0.8))
    for kind, col, s in (("std", "#bbb", 0.3), ("buf", "#7a7", 0.4), ("ff", "#36c", 0.6)):
        pts = [(float(r["x"]), float(r["y"])) for r in rows if r["kind"] == kind and not r["name"].startswith(("clkbuf", "clkload"))]
        if pts:
            a.scatter(*zip(*pts), s=s, c=col, lw=0, label=f"{kind} {len(pts)}")
    cb = [(float(r["x"]), float(r["y"])) for r in rows if r["name"].startswith(("clkbuf", "clkload"))]
    if cb:
        a.scatter(*zip(*cb), s=6, c="r", marker="s", lw=0, label=f"clock buffers {len(cb)}")
    ck = [r for r in pins if r["name"].startswith(("ck", "rst_n"))]
    for r in ck:
        a.plot(float(r["x"]), float(r["y"]), "m*", ms=12)
    a.text(W / 2, H + 3, "ck[0..2] / rst_n (N-face centre)", ha="center", color="m")
    a.set_xlim(-5, W + 5); a.set_ylim(-5, H + 12); a.set_aspect("equal"); a.legend(loc="lower right", fontsize=8, markerscale=6)
    a.set_title(f"{fz['type']} after CTS ({kd})")
    b = ax[1]
    ar = list(csv.DictReader(open(arr)))
    xs, ys, vs = [], [], []
    for r in ar:
        x, y = float(r["x"]), float(r["y"])
        if x == 0 and y == 0:
            inst = r["name"].rsplit("/", 1)[0]
            p = pos.get(inst)
            if not p:
                continue
            x, y = float(p["x"]), float(p["y"])
        xs.append(x); ys.append(y); vs.append(float(r["arrival_ps"]))
    sc = b.scatter(xs, ys, c=vs, s=2, cmap="viridis", lw=0)
    fig.colorbar(sc, ax=b, label="clock arrival ps (TC, raw CTS)")
    for r in ck:
        b.plot(float(r["x"]), float(r["y"]), "m*", ms=12)
    b.set_xlim(-5, W + 5); b.set_ylim(-5, H + 12); b.set_aspect("equal")
    st = dict(n=len(vs), min=min(vs), mean=sum(vs) / len(vs), max=max(vs)) if vs else {}
    b.set_title("register clock arrival: " + ", ".join(f"{k} {v:.1f}" if isinstance(v, float) else f"{k} {v}" for k, v in st.items()))
    fig.tight_layout()
    fig.savefig(outp)
    json.dump(dict(arrival=st, clock_buffers=len(cb), macros=sum(1 for r in rows if r["kind"] == "macro")),
              open(outp + ".json", "w"), indent=1)
    print(json.dumps(st))


if __name__ == "__main__":
    main(*sys.argv[1:5])
