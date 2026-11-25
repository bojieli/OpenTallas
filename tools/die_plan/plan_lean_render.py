#!/usr/bin/env python3
"""plan_lean_render.py -- FP-CONVERGE lean plan renderer (no tap_grid / reset-tree solve; seconds, not minutes).

    plan_lean_render.py PLAN.json OUTDIR [--types a,b,...] [--kit-sinks kit_sinks.json] [--reach 405]

OUTDIR/die.png: die outline, every partition rectangle (colour by type family), die channels (hatched).
OUTDIR/type_<name>.png: type outline, hard cores (grey), planned taps (red star, label = planned sink count by nearest-tap
assignment of clock.sink_sites_um bins, red when > 1000; the kit-measured max tap is in the title), internal-station chains
(green hops <= reach, red hops > reach), ft slots.  A type name given as a prefix resolves to its first match."""
import argparse
import json
import math
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402


def fam(t):
    return re.sub(r"__.*", "", t)


def die_png(P, out):
    d = P["die"]
    W, H = d["outline_um"]
    ty = P["partition_types"]
    fams = sorted({fam(p["type"]) for p in P["partitions"]})
    cmap = plt.get_cmap("tab20")
    col = {f: cmap(i % 20) for i, f in enumerate(fams)}
    fig, ax = plt.subplots(figsize=(16, 16 * H / W + 1))
    ax.add_patch(Rectangle((0, 0), W, H, fill=False, lw=1.5))
    for c in d.get("channels", []):
        x0, y0, x1, y1 = c["rect_um"]
        ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fill=False, hatch="///", ec="0.6", lw=0.3))
    for p in P["partitions"]:
        t = ty.get(p["type"]) or {}
        w, h = t.get("outline_um", [0, 0])
        if p.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90"):
            w, h = h, w
        x, y = p["origin_um"]
        ax.add_patch(Rectangle((x, y), w, h, fc=col[fam(p["type"])], ec="k", lw=0.2, alpha=0.8))
    for f in fams:
        ax.plot([], [], "s", color=col[f], label=f)
    ax.legend(fontsize=5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.02))
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_title(f"{d.get('name')} die {W:.0f}x{H:.0f} um: {len(P['partitions'])} partitions, {len(fams)} families, "
                 f"{len(d.get('channels', []))} channels")
    fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)


def type_png(P, name, out, kit, reach):
    t = P["partition_types"][name]
    w, h = t["outline_um"]
    ck = t.get("clock") or {}
    taps = ck.get("taps") or []
    bins = ck.get("sink_sites_um") or []
    cnt = {tp["name"]: 0.0 for tp in taps}
    for b in bins:
        if not taps:
            break
        bx, by, bw = b[0], b[1], (b[2] if len(b) > 2 else 1)
        n = min(taps, key=lambda tp: (tp["xy"][0] - bx) ** 2 + (tp["xy"][1] - by) ** 2)
        cnt[n["name"]] += bw
    fig, ax = plt.subplots(figsize=(11, 11 * h / w + 1))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
    for c in t.get("hard_cores", []) or []:
        o = c.get("origin_um"); s = c.get("outline_um")
        if o and s:
            rw, rh = (s[1], s[0]) if c.get("orient", "R0") in ("R90", "R270", "MXR90", "MYR90") else s
            ax.add_patch(Rectangle(o, rw, rh, fc="0.75", ec="0.3", lw=0.3))
    nlong = 0
    for e in t.get("internal_stations") or []:
        pts = [e.get("from_um")] + list(e.get("regs_um") or []) + [e.get("to_um")]
        pts = [p for p in pts if p]
        for a, b in zip(pts, pts[1:]):
            L = abs(a[0] - b[0]) + abs(a[1] - b[1])
            bad = L > reach
            nlong += bad
            ax.plot([a[0], b[0]], [a[1], b[1]], "-", color="red" if bad else "green", lw=1.2 if bad else 0.4, alpha=0.8)
    for s in t.get("ft_slots") or []:
        for r in s.get("regs_um") or []:
            ax.plot(r[0], r[1], ".", color="orange", ms=1.5)
    over = 0
    for tp in taps:
        n = cnt.get(tp["name"], 0)
        bad = n > 1000
        over += bad
        ax.plot(*tp["xy"], "*", color="red" if bad else "blue", ms=7 if bad else 3)
        if n >= 300:
            ax.annotate(f"{n:.0f}", tp["xy"], fontsize=5, color="red" if bad else "k")
    km = (kit or {}).get(name, {})
    ax.set_xlim(-20, w + 20); ax.set_ylim(-20, h + 20); ax.set_aspect("equal")
    ax.set_title(f"{name} {w:.0f}x{h:.0f}: {len(taps)} taps, planned >1000: {over}, hops>{reach:.0f}um: {nlong}, "
                 f"kit max tap {km.get('max_sinks', 'n/a')} ({km.get('max_tap', '')})", fontsize=8)
    fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
    return over, nlong


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("plan"); ap.add_argument("outdir")
    ap.add_argument("--types", default="")
    ap.add_argument("--kit-sinks", default="")
    ap.add_argument("--reach", type=float, default=405.0)
    a = ap.parse_args(argv)
    P = json.loads(Path(a.plan).read_text())
    out = Path(a.outdir); out.mkdir(parents=True, exist_ok=True)
    kit = json.loads(Path(a.kit_sinks).read_text()) if a.kit_sinks else {}
    die_png(P, out / "die.png")
    for n in [x for x in a.types.split(",") if x]:
        full = n if n in P["partition_types"] else next((k for k in sorted(P["partition_types"]) if k.startswith(n)), None)
        if not full:
            print("no type", n, file=sys.stderr); continue
        print(full, type_png(P, full, out / f"type_{full}.png", kit, a.reach))
    return 0


if __name__ == "__main__":
    sys.exit(main())
