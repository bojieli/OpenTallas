#!/usr/bin/env python3
"""Static die-FT cut check per partition type (DIE-FT-HBM 2026-10-25).

Every ft slot of a type is drawn as a rectilinear path from its in-face pin window centroid to its out-face pin window
centroid (E/W -> E/W: Z with the vertical jog at mid-width; N/S -> N/S: Z with the jog at mid-height; turns: L through
the corner).  At every cut (each `step` um, vertical cuts for H demand and horizontal cuts for V demand) demand = bits
whose path crosses the cut, capacity = the die's tracks across the cut: H layers M4/M6 (V: M5/M7) per um at the die share
(ft_track_frac, default 0.25), 0 where a planned hard core with top >= layer covers the layer (as die_trial core_obs), and
at the band die_share inside a type's die_ft_bands (die-owned layers; die_trial models them with GRT region
adjustments).  Ratio rule: <= 0.55-0.60 (OWNER 10-12 cut analysis).  Also: FT face pins outside the type's bands
(`pins_out_of_band`).  Light: plan JSON only, no OpenROAD."""
import json, sys
from collections import defaultdict
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import schema as S, gen_phys  # noqa: E402
import die_trial as D  # noqa: E402

PITCH = dict(M4=0.048, M5=0.048, M6=0.064, M7=0.064)
HL, VL = ("M4", "M6"), ("M5", "M7")


def merged_len(iv):
    iv = sorted(iv)
    tot, cur = 0.0, None
    for a, b in iv:
        if cur is None or a > cur[1]:
            if cur:
                tot += cur[1] - cur[0]
            cur = [a, b]
        else:
            cur[1] = max(cur[1], b)
    return tot + (cur[1] - cur[0] if cur else 0.0)


def cut_capacity(t, horiz_demand, c, share):
    """tracks across the cut at coordinate c (x for H demand, y for V demand)."""
    w, h = t["outline_um"]
    L = h if horiz_demand else w
    layers = HL if horiz_demand else VL
    cores = D.core_obs(t)
    bands = [b for b in t.get("die_ft_bands", []) or [] if (b["dir"] == "EW") == horiz_demand]
    tot = 0.0
    for ln in layers:
        lv = int(ln[1:])
        blk = []
        for x0, y0, x1, y1, tl, *_ in cores:
            if int(tl[1:]) < lv:
                continue
            if horiz_demand and x0 <= c <= x1:
                blk.append((y0, y1))
            if not horiz_demand and y0 <= c <= y1:
                blk.append((x0, x1))
        free = L - merged_len([(max(0, a), min(L, b)) for a, b in blk])
        bfree_tot = 0.0
        for b in bands:
            if ln not in b["layers"]:
                continue
            lo, hi = b["span_um"]
            bfree = (hi - lo) - merged_len([(max(lo, a), min(hi, bb)) for a, bb in blk if bb > lo and a < hi])
            bfree_tot += bfree
            tot += bfree / PITCH[ln] * b.get("die_share", 1.0)
        tot += (free - bfree_tot) / PITCH[ln] * share
    return tot


def slot_paths(P, tn):
    t = P.types[tn]
    w, h = t["outline_um"]
    pins = defaultdict(list)
    for bus, bit, ln, x, y, f in gen_phys.type_pins(P, tn):
        pins[bus].append((x, y, f))
    out = []
    for s in t.get("ft_slots", []) or []:
        a, b = pins.get(s["name"] + "_i"), pins.get(s["name"] + "_o")
        if not a or not b:
            continue
        ca = (sum(p[0] for p in a) / len(a), sum(p[1] for p in a) / len(a), s["in_face"])
        cb = (sum(p[0] for p in b) / len(b), sum(p[1] for p in b) / len(b), s["out_face"])
        fa, fb = ca[2], cb[2]
        if fa in "EW" and fb in "EW":
            xm = w / 2 if fa != fb else (w * 0.25 if fa == "W" else w * 0.75)
            pts = [ca[:2], (xm, ca[1]), (xm, cb[1]), cb[:2]]
        elif fa in "NS" and fb in "NS":
            ym = h / 2 if fa != fb else (h * 0.25 if fa == "S" else h * 0.75)
            pts = [ca[:2], (ca[0], ym), (cb[0], ym), cb[:2]]
        elif fa in "NS":
            pts = [ca[:2], (ca[0], cb[1]), cb[:2]]
        else:
            pts = [ca[:2], (cb[0], ca[1]), cb[:2]]
        out.append((s["name"], int(s["width"]), pts, a + b))
    return out


def type_report(P, tn, share, step=25.0):
    t = P.types[tn]
    w, h = t["outline_um"]
    paths = slot_paths(P, tn)
    res = {}
    for horiz in (True, False):
        L = w if horiz else h
        worst = (0.0, None, 0, 0)
        k = step / 2
        while k < L:
            dem = 0
            for _, wd, pts, _ in paths:
                for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
                    if horiz and y0 == y1 and min(x0, x1) < k < max(x0, x1):
                        dem += wd
                        break
                    if not horiz and x0 == x1 and min(y0, y1) < k < max(y0, y1):
                        dem += wd
                        break
            if dem:
                cap = cut_capacity(t, horiz, k, share)
                r = dem / cap if cap else 99.0
                if r > worst[0]:
                    worst = (round(r, 3), round(k, 1), dem, round(cap))
            k += step
        res["cut_h" if horiz else "cut_v"] = worst
    oob = 0
    bands = t.get("die_ft_bands", []) or []
    if bands:
        for _, wd, pts, pp in paths:
            for x, y, f in pp:
                ok = False
                for b in bands:
                    lo, hi = b["span_um"]
                    c = y if b["dir"] == "EW" else x
                    if (f in "EW") == (b["dir"] == "EW") and lo <= c <= hi:
                        ok = True
                if not ok and (f in "EW") == any(b["dir"] == "EW" for b in bands):
                    oob += 1
    res["pins_out_of_band"] = oob
    return res


def main(plan, share=None, types=None):
    P = S.Plan(S.load(plan))
    if share is None:
        share = min(t.get("ft_track_frac", 0.25) for t in P.types.values())
    rows = []
    for tn in sorted(P.types):
        if types and tn not in types:
            continue
        if not P.types[tn].get("ft_slots"):
            continue
        r = type_report(P, tn, share)
        r["type"] = tn
        r["wh"] = P.types[tn]["outline_um"]
        r["bands"] = P.types[tn].get("die_ft_bands", [])
        rows.append(r)
    rows.sort(key=lambda r: -max(r["cut_h"][0], r["cut_v"][0]))
    return rows


if __name__ == "__main__":
    import argparse
    a = argparse.ArgumentParser()
    a.add_argument("plan"); a.add_argument("--share", type=float); a.add_argument("--top", type=int, default=20)
    a.add_argument("--types", nargs="*"); a.add_argument("--json")
    x = a.parse_args()
    rows = main(x.plan, x.share, x.types)
    for r in rows[:x.top]:
        print(r["type"], r["wh"], "cut_h(ratio,x,dem,cap)", r["cut_h"], "cut_v(ratio,y,dem,cap)", r["cut_v"],
              "oob", r["pins_out_of_band"], "bands", len(r["bands"]))
    if x.json:
        Path(x.json).write_text(json.dumps(rows, indent=0))
