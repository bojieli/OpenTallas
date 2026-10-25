#!/usr/bin/env python3
"""CORE-HBM placed render + stats from dump_placed.py CSV and the kit's ot_face_flops.txt.
    python3 render_core_placed.py KITDIR placed.csv face_flops.txt OUTPNG  -> OUTPNG + OUTPNG.json
Stats: std fill of free area (core area minus macros+halo), buf/inv share, density bins > 0.8 (10-um bins),
face-flop pin->reg distance p50/p90/max (Manhattan, flop origin to its pin)."""
import csv
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402


def main(kd, csvf, fff, outp):
    fz = json.load(open(Path(kd) / "freeze.json"))
    W, H = fz["outline_um"]
    rows = list(csv.DictReader(open(csvf)))
    inst = [r for r in rows if r["kind"] != "pin"]
    pins = {r["name"]: r for r in rows if r["kind"] == "pin"}
    pos = {r["name"]: r for r in inst}
    m = 4.32
    core = (W - 2 * m) * (H - 2 * m)
    mac = [r for r in inst if r["kind"] == "macro"]
    mac_a = sum((float(r["w"]) + 4.32) * (float(r["h"]) + 4.32) for r in mac)
    std = [r for r in inst if r["kind"] in ("std", "ff", "buf")]
    std_a = sum(float(r["w"]) * float(r["h"]) for r in std)
    buf_a = sum(float(r["w"]) * float(r["h"]) for r in std if r["kind"] == "buf")
    nb = int(np.ceil(W / 10)), int(np.ceil(H / 10))
    den = np.zeros(nb)
    for r in std:
        x, y = float(r["x"]), float(r["y"])
        den[min(nb[0] - 1, int(x / 10)), min(nb[1] - 1, int(y / 10))] += float(r["w"]) * float(r["h"]) / 100.0
    d = []
    if Path(fff).is_file():
        for ln in open(fff):
            f = ln.rstrip("\n").split("\t")
            if len(f) >= 5 and f[0] in pos and f[4] in pins:
                p, q = pins[f[4]], pos[f[0]]
                d.append(abs(float(p["x"]) - float(q["x"])) + abs(float(p["y"]) - float(q["y"])))
    d.sort()
    st = dict(type=fz["view"], kit_hash=fz["kit_hash"], outline_um=[W, H], cells=len(std), ffs=sum(r["kind"] == "ff" for r in std),
              macros=len(mac), std_area_um2=round(std_a, 1), free_area_um2=round(core - mac_a, 1),
              fill_of_free=round(std_a / max(1.0, core - mac_a), 3), bufinv_area_share=round(buf_a / max(1.0, std_a), 3),
              bins_over_0p8=int((den > 0.8).sum()), max_bin=round(float(den.max()), 2), face_flops=len(d),
              pin_reg_um=dict(p50=round(d[len(d) // 2], 1) if d else None, p90=round(d[int(len(d) * 0.9)], 1) if d else None,
                              max=round(d[-1], 1) if d else None))
    fig, ax = plt.subplots(figsize=(10, 10 * H / W), dpi=130)
    ax.imshow(den.T, origin="lower", extent=(0, nb[0] * 10, 0, nb[1] * 10), cmap="Greys", vmin=0, vmax=1.0)
    for r in mac:
        ax.add_patch(plt.Rectangle((float(r["x"]), float(r["y"])), float(r["w"]), float(r["h"]), fill=False, ec="tab:blue", lw=1.2))
        ax.text(float(r["x"]) + 2, float(r["y"]) + 2, r["master"][-22:], fontsize=5, color="tab:blue")
    ff = [r for r in std if r["kind"] == "ff"]
    ax.scatter([float(r["x"]) for r in ff], [float(r["y"]) for r in ff], s=0.3, color="tab:green", alpha=0.4, label=f"flops {len(ff)}")
    ax.scatter([float(p["x"]) for p in pins.values()], [float(p["y"]) for p in pins.values()], s=1.5, color="tab:red", label=f"pins {len(pins)}")
    ax.add_patch(plt.Rectangle((0, 0), W, H, fill=False, lw=1.0))
    ax.set_xlim(-5, W + 5)
    ax.set_ylim(-5, H + 5)
    ax.set_aspect("equal")
    ax.legend(fontsize=7, loc="upper right")
    ax.set_title(f"{fz['view']} placed: fill {st['fill_of_free']:.0%} of free, buf/inv {st['bufinv_area_share']:.0%} area, "
                 f"bins>0.8 {st['bins_over_0p8']}, pin->reg p90 {st['pin_reg_um']['p90']} um\nkit {fz['kit_hash']} plan "
                 f"{fz['plan_sha256'][:12]} pins {fz['pins_sha256'][:12]}", fontsize=8)
    fig.tight_layout()
    fig.savefig(outp)
    Path(outp + ".json").write_text(json.dumps(st, indent=1) + "\n")
    print(json.dumps(st))


if __name__ == "__main__":
    main(*sys.argv[1:5])
