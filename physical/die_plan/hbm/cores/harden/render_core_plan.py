#!/usr/bin/env python3
"""CORE-HBM plan render + face stats of a core kit: outline, every plan pin (by layer), per-face pins/um, the worst
10-um window, pins/track, SRAM macro footprint (from the kit LEFs x instance count if given).

    python3 render_core_plan.py KITDIR [--srams N:MACRO ...]   -> KITDIR/plan_render.png + KITDIR/plan_stats.json
"""
import collections
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)   # plan M4-M7 pitches (ASAP7)


def main(kd):
    kd = Path(kd)
    fz = json.load(open(kd / "freeze.json"))
    w, h = fz["outline_um"]
    pins = json.load(open(kd / "pins.json"))
    by = collections.defaultdict(list)
    for p in pins:
        by[p["face"]].append(p)
    stats = dict(type=fz["type"], outline_um=[w, h], pins=len(pins), area_um2=round(w * h, 1), faces={})
    for f, L in sorted(by.items()):
        span = h if f in "EW" else w
        co = sorted(p["y"] if f in "EW" else p["x"] for p in L)
        win = 0
        j = 0
        for i in range(len(co)):
            while co[i] - co[j] > 10.0:
                j += 1
            win = max(win, i - j + 1)
        lay = collections.Counter(p["layer"] for p in L)
        tracks = sum(span / PITCH.get(l, 0.048) for l in lay)
        stats["faces"][f] = dict(pins=len(L), span_um=span, per_um=round(len(L) / span, 2),
                                 max_10um=win, max_10um_per_um=round(win / 10.0, 2), layers=dict(lay),
                                 pin_per_track=round(len(L) / tracks, 3) if tracks else None,
                                 extent_um=[round(co[0], 2), round(co[-1], 2)])
    worst = max(v["max_10um_per_um"] for v in stats["faces"].values())
    stats["worst_10um_per_um"] = worst
    stats["face_rule"] = "PASS" if worst <= 6.0 and all(v["per_um"] <= 6.0 for v in stats["faces"].values()) else "FAIL"
    fig, ax = plt.subplots(figsize=(9, 9 * h / w if w else 9), dpi=120)
    ax.add_patch(plt.Rectangle((0, 0), w, h, fill=False, lw=1.2))
    ax.add_patch(plt.Rectangle((4.32, 4.32), w - 8.64, h - 8.64, fill=False, lw=0.5, ls="--", color="grey"))
    col = dict(M4="tab:blue", M5="tab:red", M3="tab:green", M6="tab:purple", M7="tab:orange")
    for l in sorted({p["layer"] for p in pins}):
        P = [p for p in pins if p["layer"] == l]
        ax.scatter([p["x"] for p in P], [p["y"] for p in P], s=3, color=col.get(l, "k"), label=f"{l} ({len(P)})")
    for f, v in stats["faces"].items():
        tx, ty = dict(W=(-0.02 * w, h / 2), E=(1.0 * w, h / 2), S=(w / 2, -0.04 * h), N=(w / 2, 1.01 * h))[f]
        ax.text(tx, ty, f"{f}: {v['pins']} pins, {v['per_um']}/um, max10 {v['max_10um_per_um']}/um", fontsize=7,
                ha="center", rotation=90 if f in "EW" else 0, va="center")
    ax.set_xlim(-0.08 * w, 1.08 * w)
    ax.set_ylim(-0.08 * h, 1.08 * h)
    ax.set_aspect("equal")
    ax.legend(fontsize=7, loc="center")
    ax.set_title(f"{fz['type']}  {w:g} x {h:g} um, {len(pins)} pins, face rule {stats['face_rule']} "
                 f"(worst 10-um {worst}/um)\nplan {fz['plan_commit']} pins {fz['pins_sha256'][:12]} kit "
                 f"{fz['kit_hash']}", fontsize=8)
    fig.tight_layout()
    fig.savefig(kd / "plan_render.png")
    (kd / "plan_stats.json").write_text(json.dumps(stats, indent=1) + "\n")
    print(json.dumps(dict(type=fz["type"], pins=len(pins), face_rule=stats["face_rule"], worst=worst,
                          faces={f: (v["pins"], v["per_um"], v["max_10um_per_um"]) for f, v in stats["faces"].items()})))


if __name__ == "__main__":
    for k in sys.argv[1:]:
        main(k)
