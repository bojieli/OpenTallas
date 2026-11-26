#!/usr/bin/env python3
"""plan_lean_render.py -- FP-CONVERGE lean plan renderer (no tap_grid / reset-tree solve; seconds, not minutes).

    plan_lean_render.py PLAN.json OUTDIR [--types a,b,...] [--kit-sinks kit_sinks.json] [--reach 405]

OUTDIR/die.png: die outline, every partition rectangle (colour by type family), die channels (hatched), PG domain rects
(dashed; the plan carries M8/M9 grids only for the PHY domains).
OUTDIR/type_<name>.png: type outline, hard cores (grey), planned taps (blue star; red when its planned sink count by
nearest-tap assignment of clock.sink_sites_um > 1000; the kit-measured max tap is in the title), clock.added_taps (cyan
star, same counting), internal-station chains drawn as Manhattan L-shapes (green <= reach, red > reach), ft slots as
polylines in-window -> registers -> out-window (blue <= reach, red > reach, stations as dots; a station outside the
outline is a magenta X and the axes grow to it), core-to-core slots 0 < gap < SLOT_UM shaded orange, core overlaps
magenta.  Hop length is Manhattan and ft hops count in the > reach total.  A type name given as a prefix resolves to its
first match.  Not drawn: PG straps inside a type (the plan has none there; count_straps are tie-offs, not geometry)."""
import argparse
import json
import re
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Rectangle  # noqa: E402

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "precheck"))
import adv_ft_outside as FO  # noqa: E402  ADV-FT-OUTSIDE: the same hit test as the PRE check
import adv_slot_gap as SG  # noqa: E402  ADV-SLOT-GAP: the same slot test as the PRE check
import precheck as PC  # noqa: E402  REACH (WINDOW-HOP, GATE/AIM) and tap_assign: the same functions as the census
from schema import placed_macro_boxes  # noqa: E402

SLOT_UM = 28.0
GEOM_EPS = 1e-6
ROT = ("R90", "R270", "MXR90", "MYR90")
LAST = {}     # extra counts of the last type_png call


def fam(t):
    return re.sub(r"__.*", "", t)


def manhattan(ax, a, b, **kw):
    """a -> b as an L (x first): the path the Manhattan hop length is measured on"""
    ax.plot([a[0], b[0], b[0]], [a[1], a[1], b[1]], **kw)


def core_rect(c):
    if not (c.get("origin_um") and c.get("outline_um")):
        return None
    return placed_macro_boxes({"hard_cores": [dict(c, inst="core")]})["core"]


def core_slots(rects, slot=SLOT_UM):
    """[(x0, y0, x1, y1, gap)]: the strip between two cores that face each other at 0 < gap < slot um; gap < 0 = overlap
    (the intersection box, gap = -min(overlap x, overlap y)).  Abutting cores (gap 0) are fine."""
    out = []
    for i, a in enumerate(rects):
        for b in rects[i + 1:]:
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            if ox > GEOM_EPS and oy > GEOM_EPS:
                out.append((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3]), -min(ox, oy)))
            elif oy > GEOM_EPS and GEOM_EPS < -ox < slot:
                lo, hi = (a, b) if a[2] <= b[0] else (b, a)
                out.append((lo[2], max(a[1], b[1]), hi[0], min(a[3], b[3]), -ox))
            elif ox > GEOM_EPS and GEOM_EPS < -oy < slot:
                lo, hi = (a, b) if a[3] <= b[1] else (b, a)
                out.append((max(a[0], b[0]), lo[3], min(a[2], b[2]), hi[1], -oy))
    return out


def man(a, b):
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def ft_chain(slot, w, h):
    """[(x, y)] of an ft slot: in-window centre on the in face, the registers, out-window centre on the out face"""
    def face(f, win):
        c = (win[0] + win[1]) / 2 if win else 0
        return {"N": (c, h), "S": (c, 0), "W": (0, c), "E": (w, c)}.get(f)
    regs = [tuple(r) for r in slot.get("regs_um") or []]
    pts = [face(slot.get("in_face"), slot.get("in_window_um"))] + regs + [face(slot.get("out_face"), slot.get("out_window_um"))]
    return [p for p in pts if p]


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
        if p.get("orient", "R0") in ROT:
            w, h = h, w
        x, y = p["origin_um"]
        ax.add_patch(Rectangle((x, y), w, h, fc=col[fam(p["type"])], ec="k", lw=0.2, alpha=0.8))
    npg = 0
    for dom in (d.get("pg") or {}).get("domains", []) or []:
        for r in [dom.get("bumps", {}).get("rect_um")] + list(dom.get("core_strip_um") or []):
            if r:
                npg += 1
                ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fill=False, ls="--", ec="red", lw=0.8))
    for f in fams:
        ax.plot([], [], "s", color=col[f], label=f)
    ax.legend(fontsize=5, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.02))
    ax.set_xlim(0, W); ax.set_ylim(0, H); ax.set_aspect("equal")
    ax.set_title(f"{d.get('name')} die {W:.0f}x{H:.0f} um: {len(P['partitions'])} partitions, {len(fams)} families, "
                 f"{len(d.get('channels', []))} channels, {npg} PG rects (red dashed)")
    fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)


def checker_numbers(t, reach, taps_xy, bins):
    """Header numbers computed by the SAME functions as the checkers, so a render can never disagree with PRE / precheck
    (t57: the header said hops>405: 0 while precheck.reach_findings found a 450.7 um leafdn first hop measured from the far
    end of its pin window).  -> dict(reach_gate, reach_aim, reach_worst, ft_out_sites, ft_out_regs, slots, tap_over)"""
    rf = PC.reach_findings(t, reach)
    gate = [v for v, _ in rf if PC.reach_severity(v) == "GATE"]
    out = FO.type_hits(t)
    cnt = PC.tap_assign(taps_xy, bins) if taps_xy and bins else {}
    return dict(reach_gate=len(gate), reach_aim=len(rf) - len(gate), reach_worst=max([v for v, _ in rf], default=0.0),
                ft_out_sites=sum(h[1] for h in out), ft_out_regs=sum(h[2] for h in out),
                slots=len(SG.slot_gaps(t)), tap_over=sum(1 for v in cnt.values() if v > 1000))


def type_png(P, name, out, kit, reach):
    t = P["partition_types"][name]
    w, h = t["outline_um"]
    ck = t.get("clock") or {}
    taps = [(tp, "plan") for tp in ck.get("taps") or []]
    seen = {tp["name"] for tp, _ in taps}
    added = [tp for tp in ck.get("added_taps") or [] if tp.get("name") not in seen]
    taps += [(tp, "added") for tp in added]
    bins = ck.get("sink_sites_um") or []
    cnt = {tp["name"]: 0.0 for tp, _ in taps}
    for b in bins:
        if not taps:
            break
        bx, by, bw = b[0], b[1], (b[2] if len(b) > 2 else 1)
        n = min(taps, key=lambda tk: (tk[0]["xy"][0] - bx) ** 2 + (tk[0]["xy"][1] - by) ** 2)[0]
        cnt[n["name"]] += bw
    fig, ax = plt.subplots(figsize=(11, 11 * h / w + 1))
    ax.add_patch(Rectangle((0, 0), w, h, fill=False, lw=1.5))
    rects = []
    for c in t.get("hard_cores", []) or []:
        r = core_rect(c)
        if r:
            rects.append(r)
            ax.add_patch(Rectangle((r[0], r[1]), r[2] - r[0], r[3] - r[1], fc="0.75", ec="0.3", lw=0.3))
    nslot = nover = 0
    for x0, y0, x1, y1, gap in core_slots(rects):
        if gap < 0:
            nover += 1
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, fc="magenta", ec="magenta", lw=0.6, alpha=0.9))
        else:
            nslot += 1
            ax.add_patch(Rectangle((x0, y0), max(x1 - x0, 1.5), max(y1 - y0, 1.5), fc="orange", ec="darkorange", lw=0.4, alpha=0.8))
    xs, ys = [0, w], [0, h]
    nlong = 0
    for e in t.get("internal_stations") or []:
        pts = [p for p in [e.get("from_um")] + list(e.get("regs_um") or []) + [e.get("to_um")] if p]
        for a, b in zip(pts, pts[1:]):
            bad = man(a, b) > reach
            nlong += bad
            manhattan(ax, a, b, color="red" if bad else "green", lw=1.2 if bad else 0.4, alpha=0.8)
    nft = nftlong = nout = 0
    for s in t.get("ft_slots") or []:
        pts = ft_chain(s, w, h)
        nft += 1
        for a, b in zip(pts, pts[1:]):
            bad = man(a, b) > reach
            nftlong += bad
            manhattan(ax, a, b, color="red" if bad else "royalblue", lw=1.4 if bad else 0.6, alpha=0.85)
        for r in s.get("regs_um") or []:
            if 0 <= r[0] <= w and 0 <= r[1] <= h:
                ax.plot(r[0], r[1], ".", color="orange", ms=3)
            else:
                nout += 1
                ax.plot(r[0], r[1], "X", color="magenta", ms=9)
                xs.append(r[0]); ys.append(r[1])
        if pts:
            ax.annotate(s.get("name", ""), pts[0], fontsize=5, color="royalblue")
    over = 0
    for tp, kind in taps:
        n = cnt.get(tp["name"], 0)
        bad = n > 1000
        over += bad
        ax.plot(*tp["xy"], "*", color="red" if bad else ("c" if kind == "added" else "blue"), ms=7 if bad else 3)
        if n >= 300:
            ax.annotate(f"{n:.0f}", tp["xy"], fontsize=5, color="red" if bad else "k")
    cn = checker_numbers(t, PC.REACH_UM, [(tp["name"], tp["xy"][0], tp["xy"][1]) for tp, _ in taps],
                         [(b[0], b[1], (b[2] if len(b) > 2 else 1)) for b in bins])
    km = (kit or {}).get(name, {})
    ax.set_xlim(min(xs) - 20, max(xs) + 20); ax.set_ylim(min(ys) - 20, max(ys) + 20); ax.set_aspect("equal")
    ax.set_title(f"{name} {w:.0f}x{h:.0f}: {len(taps) - len(added)}+{len(added)} added taps, planned >1000 (plan bins only): {cn['tap_over']}, "
                 f"REACH (precheck): {cn['reach_gate']} GATE >{PC.CBC.REACH_GATE_UM:.0f}um + {cn['reach_aim']} AIM, worst {cn['reach_worst']:.0f}um "
                 f"({nlong} chains + {nftlong} ft drawn red, {nft} ft slots), ft outside outline (ADV-FT-OUTSIDE): "
                 f"{cn['ft_out_sites']} sites + {cn['ft_out_regs']} regs, "
                 f"slots<{SLOT_UM:.0f}um (ADV-SLOT-GAP): {cn['slots']}, core overlaps: {nover}, kit max tap {km.get('max_sinks', 'n/a')} "
                 f"({km.get('max_tap', '')})", fontsize=7)
    LAST.clear()
    LAST.update(checker=cn, ft_long=nftlong, out_of_outline=nout, slots=nslot, overlaps=nover, added_taps=len(added), chain_long=nlong)
    fig.savefig(out, dpi=110, bbox_inches="tight"); plt.close(fig)
    return over, nlong + nftlong


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
        print(full, type_png(P, full, out / f"type_{full}.png", kit, a.reach), dict(LAST))
    return 0


if __name__ == "__main__":
    sys.exit(main())
