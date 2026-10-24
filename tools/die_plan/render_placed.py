#!/usr/bin/env python3
"""Placed partition render for the G3 visual review (S81-P10 10-24).

    python3 tools/die_plan/render_placed.py KITDIR placed.csv probe.json OUT.png

placed.csv: physical/die_plan/s81/cores/svc/dump_placed.py rows (kind,name,master,x,y,w,h).  Draws macros (grey,
labelled by master), std-cell density (20-um bins), soft relay stations u_y_* (orange), face pins from pins.json, the
clock / reset taps, and the probe's over-limit reg-reg pairs (red lines, one per group).  OUT.png.json: stats (cells,
FF, buf/inv share, max bin density, min macro gap, taps on macros).
"""
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main(kd, csvf, probef, outp):
    kd = Path(kd)
    bud = json.load(open(kd / "budget.json")) if (kd / "budget.json").exists() else {}
    cfg = (kd / "config.mk").read_text()
    die = [float(x) for x in cfg.split("DIE_AREA =")[1].split("\n")[0].split()]
    W, H = die[2], die[3]
    rows = list(csv.DictReader(open(csvf)))
    inst = [r for r in rows if r["kind"] not in ("pin", "tap")]
    mac = [r for r in inst if r["kind"] == "macro"]
    std = [r for r in inst if r["kind"] in ("std", "ff", "buf")]
    rly = [r for r in std if ".u_y_" in r["name"] or r["name"].startswith("u_y_")]
    B = 20.0
    nx, ny = int(np.ceil(W / B)), int(np.ceil(H / B))
    dens = np.zeros((ny, nx))
    for r in std:
        x, y, w, h = (float(r[k]) for k in "xywh")
        dens[min(int(y / B), ny - 1), min(int(x / B), nx - 1)] += w * h
    dens /= B * B
    fig, ax = plt.subplots(figsize=(14, 14 * H / W))
    ax.imshow(dens, origin="lower", extent=(0, nx * B, 0, ny * B), cmap="Blues", vmin=0, vmax=0.8, alpha=0.9)
    for r in mac:
        x, y, w, h = (float(r[k]) for k in "xywh")
        ax.add_patch(plt.Rectangle((x, y), w, h, fc="0.6", ec="k", lw=0.4, alpha=0.75))
        if w * h > 2000:
            ax.text(x + w / 2, y + h / 2, r["master"][:22], fontsize=4, ha="center", va="center")
    if rly:
        ax.scatter([float(r["x"]) for r in rly], [float(r["y"]) for r in rly], s=0.3, c="orange", label="u_y_* relays")
    pins = json.load(open(kd / "pins.json")) if (kd / "pins.json").exists() else []
    if pins:
        ax.scatter([p["x"] for p in pins], [p["y"] for p in pins], s=0.5, c="green", label="face pins")
    pr = json.load(open(probef)) if probef and Path(probef).exists() else {}
    for ln in pr.get("over_lines", []):
        c, x0, y0, x1, y1 = ln
        ax.plot([x0, x1], [y0, y1], c="red" if "data" in c else "magenta", lw=0.6)
    taps = [r for r in rows if r["kind"] == "pin" and (r["name"].startswith("clk") or r["name"] == "arst_n")]
    for t in taps:
        ax.plot(float(t["x"]), float(t["y"]), "k^", ms=4)
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.set_aspect("equal")
    ff = sum(1 for r in std if r["kind"] == "ff")
    buf = sum(1 for r in std if r["kind"] == "buf")
    gaps = []
    for i, a in enumerate(mac):
        ax0, ay0, aw, ah = (float(a[k]) for k in "xywh")
        best = 1e9
        for b in mac[:i] + mac[i + 1:]:
            bx0, by0, bw, bh = (float(b[k]) for k in "xywh")
            dx = max(bx0 - (ax0 + aw), ax0 - (bx0 + bw), 0)
            dy = max(by0 - (ay0 + ah), ay0 - (by0 + bh), 0)
            best = min(best, max(dx, dy) if (dx == 0 or dy == 0) else np.hypot(dx, dy))
        gaps.append(best)
    on_mac = 0
    for t in taps:
        tx, ty = float(t["x"]), float(t["y"])
        on_mac += any(float(m["x"]) <= tx <= float(m["x"]) + float(m["w"]) and float(m["y"]) <= ty <= float(m["y"]) + float(m["h"])
                      for m in mac)
    st = dict(cells=len(std), ff=ff, buf_inv=buf, buf_share=round(buf / max(1, len(std)), 3), macros=len(mac),
              relays=len(rly), max_bin_density=round(float(dens.max()), 3), bins_over_0p8=int((dens > 0.8).sum()),
              min_macro_gap_um=round(min(gaps), 2) if gaps else None, taps=len(taps), taps_on_macro=on_mac,
              over_total=pr.get("over_total"), over_data=pr.get("over_data"), outline=[W, H],
              pin_reg_p90_limit=bud.get("pin_reg_p90_um"))
    ax.set_title(f"{kd.name}: {st['cells']} cells, FF {ff}, buf/inv {st['buf_share']:.0%}, macros {len(mac)}, "
                 f"relays {len(rly)}, max dens {st['max_bin_density']}, reg-reg>750 data {st['over_data']} "
                 f"total {st['over_total']}", fontsize=9)
    ax.legend(loc="upper right", fontsize=6, markerscale=8)
    fig.savefig(outp, dpi=170, bbox_inches="tight")
    json.dump(st, open(str(outp) + ".json", "w"), indent=1)
    print(json.dumps(st))


if __name__ == "__main__":
    main(*sys.argv[1:5])
