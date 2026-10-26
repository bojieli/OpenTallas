#!/usr/bin/env python3
"""Die-plan FT cut bounds at IDEAL straight-through alignment (PATH-S81 10-26; owner question "is the S81 overflow
fundamental?").  Three reports, all at the kit FT share (ft_track_frac 0.25; die GRT layer adjustment 0.75), ASAP7
pitches M4/M5 48 nm, M6/M7 64 nm, core obstruction = highest LAYER of the core LEF (die_trial.core_obs rule, missing -> M5):
  1. seam cuts: every abutting partition pair, port bits crossing it vs vertical (N-S seams: M5+M7) or horizontal
     (E-W seams: M4+M6) tracks along the shared edge; plus die rows.
  2. vertical, per partition: N-S + turning FT bits vs tracks in full-height x columns clear of core OBS.
  3. horizontal, per partition: E-W + turning FT bits (and current N-S jogs) vs tracks in full-width clear rows.
Owner cut rule: ratio <= 0.55-0.60.
    ft_cut_bound.py PLAN [SRC_ROOT]      (SRC_ROOT = tree holding the plan's core LEFs; default: repo root of PLAN)
"""
import os
_argv_src = None

import json, sys, collections
print('== 1. seam cuts')
d = json.load(open(sys.argv[1])); T = d["partition_types"]; PA = {p["name"]: p for p in d["partitions"]}
SH = 0.25; PV = {"M5": 0.048, "M7": 0.064}; PH = {"M4": 0.048, "M6": 0.064}
def rect(n):
    p = PA[n]; w, h = T[p["type"]]["outline_um"]; return p["origin_um"][0], p["origin_um"][1], p["origin_um"][0]+w, p["origin_um"][1]+h
seam = collections.defaultdict(lambda: [0, 0, []])
for pr in d["ports"]:
    a, b = pr["src"]["part"], pr["dst"]["part"]
    if a not in PA or b not in PA: continue
    k = (min(a, b), max(a, b), "NS" if pr["face"] in "NS" else "EW")
    seam[k][0] += int(pr["width"])
    seam[k][1] += int(pr["width"]) if "ft" in pr["src"]["bus"] + pr["dst"]["bus"] else 0
rows = []
for (a, b, o), (bits, ftb, _) in seam.items():
    ra, rb = rect(a), rect(b)
    span = (min(ra[2], rb[2]) - max(ra[0], rb[0])) if o == "NS" else (min(ra[3], rb[3]) - max(ra[1], rb[1]))
    if span <= 1: continue
    L = PV if o == "NS" else PH
    full = span * sum(1 / p for p in L.values()) * SH            # both layers at FT share
    top = span * (1 / L["M7" if o == "NS" else "M6"]) * SH        # over core field (M5/M4 OBS): top layer only
    y = max(ra[1], rb[1]) if o == "NS" else max(ra[0], rb[0])
    rows.append((bits / top, bits / full, bits, ftb, span, full, top, a, b, o, y))
for o in ("NS", "EW"):
    R = sorted([r for r in rows if r[9] == o], reverse=True)
    n1 = sum(r[1] > 0.55 for r in R); n2 = sum(r[0] > 0.55 for r in R); n3 = sum(r[0] > 1 for r in R); n4 = sum(r[1] > 1 for r in R)
    print(f"== {o} cuts ({'horizontal seam, vertical tracks M5+M7' if o=='NS' else 'vertical seam, horizontal tracks M4+M6'}) n={len(R)}: "
          f">0.55 both-layers {n1}, >1.0 both-layers {n4}; >0.55 top-layer-only {n2}, >1.0 top-layer-only {n3}")
    print("  ratio_top ratio_both  bits  ft_bits span_um cap_both cap_top  seam")
    for r in R[:15]:
        print("  %6.2f %6.2f %7d %7d %7.0f %7.0f %7.0f  %s|%s y/x=%.0f" % (r[0], r[1], r[2], r[3], r[4], r[5], r[6], r[7], r[8], r[10]))
# die-wide horizontal cuts: sum of NS seam bits at the same y vs die-width capacity
byy = collections.defaultdict(lambda: [0, 0.0, 0.0])
for r in rows:
    if r[9] == "NS": byy[round(r[10], 1)][0] += r[2]; byy[round(r[10], 1)][1] += r[5]; byy[round(r[10], 1)][2] += r[6]
print("== die rows (all seams at one y): worst by both-layer ratio")
for y, (b, c, t) in sorted(byy.items(), key=lambda kv: -kv[1][0] / kv[1][1])[:8]:
    print("  y %8.1f bits %7d cap_both %7.0f ratio %.2f top-only %.2f" % (y, b, c, b / c, b / t))

print('== 2. vertical capacity over hard cores')

import numpy as np
d = json.load(open(sys.argv[1])); T = d["partition_types"]; PA = {p["name"]: p for p in d["partitions"]}
LV = {"M5": 1 / 0.048, "M7": 1 / 0.064}; ORD = {"M4": 4, "M5": 5, "M6": 6, "M7": 7}; SH = 0.25
into = {(pr["dst"]["part"], pr["dst"]["bus"]): pr for pr in d["ports"]}
import os, re as _re
SRC = sys.argv[2] if len(sys.argv) > 2 else str(__import__("pathlib").Path(sys.argv[1]).resolve().parents[3])
_top = {}
CAP_ALL = os.environ.get("FT_CUT_CAP")          # e.g. M5: what-if every hard core routes <= this layer
def lef_top(lef):
    t = _lef_top(lef)
    if CAP_ALL and ORD.get(t, 5) > ORD[CAP_ALL]: return CAP_ALL
    return t
def _lef_top(lef):
    """die_trial.core_obs rule: highest LAYER in the core LEF (missing -> M5)."""
    if not lef or not SRC: return "M5"
    for base in (SRC, os.path.join(SRC, "physical/die_plan/s81")):
        f = os.path.join(base, lef)
        if os.path.exists(f):
            if f not in _top: _top[f] = "M%d" % max([int(m) for m in _re.findall(r"LAYER\s+M(\d+)", open(f, errors="replace").read())] or [5])
            return _top[f]
    return "M5"
rows = []
for n, p in PA.items():
    t = T[p["type"]]; w, h = t["outline_um"]
    ns = sum(int(s["width"]) for s in t.get("ft_slots") or [] if {s["in_face"], s["out_face"]} == {"N", "S"} and (n, s["name"] + "_i") in into)
    turn = sum(int(s["width"]) for s in t.get("ft_slots") or [] if {s["in_face"], s["out_face"]} not in ({"N", "S"}, {"E", "W"}) and (n, s["name"] + "_i") in into)
    blk = {L: np.zeros(int(np.ceil(w)), bool) for L in LV}
    for c in t.get("hard_cores") or []:
        x0 = c["origin_um"][0]; cw = c["outline_um"][0] if c.get("orient", "R0") in ("R0", "MX", "MY", "R180") else c["outline_um"][1]
        ob = ORD.get(lef_top(c.get("lef")), 5)
        for L in LV:
            if ob >= ORD[L]: blk[L][int(max(0, x0)):int(min(w, x0 + cw + 1))] = True
    capc = sum((~blk[L]).sum() * v for L, v in LV.items())            # tracks in full-height clear columns (100%)
    capall = sum(w * v for v in LV.values())
    clear_both = int((~blk["M5"] & ~blk["M7"]).sum()); clear7 = int((~blk["M7"]).sum())
    if ns + turn == 0: continue
    rows.append(dict(part=n, type=p["type"], x=p["origin_um"][0], y=p["origin_um"][1], w=w, ns_bits=ns, turn_bits=turn,
                     clear_M5M7_um=clear_both, clear_M7_um=clear7, cap_clear_share=capc * SH, cap_nocore_share=capall * SH,
                     ratio_clear=(ns + turn) / max(1, capc * SH), ratio_nocore=(ns + turn) / (capall * SH),
                     corridor_um_share25=(ns + turn) / (sum(LV.values()) * SH), corridor_um_share50=(ns + turn) / (sum(LV.values()) * .5)))
rows.sort(key=lambda r: -r["ratio_clear"])
print("partitions with N-S/turn FT: %d; ratio_clear>0.55: %d, >1.0: %d; ratio_nocore>0.55: %d" % (len(rows), sum(r["ratio_clear"] > .55 for r in rows), sum(r["ratio_clear"] > 1 for r in rows), sum(r["ratio_nocore"] > .55 for r in rows)))
print(" part        type                         y      ns_bits turn  clearM5M7um clearM7um ratio_clear ratio_nocore corridor@25%um @50%um")
for r in rows[:22]:
    print(" %-11s %-28s %7.0f %6d %5d %8d %9d %8.2f %8.2f %9.0f %7.0f" % (r["part"], r["type"][:28], r["y"], r["ns_bits"], r["turn_bits"], r["clear_M5M7_um"], r["clear_M7_um"], r["ratio_clear"], r["ratio_nocore"], r["corridor_um_share25"], r["corridor_um_share50"]))
by = collections.defaultdict(list)
for r in rows: by[r["part"].split("_")[-1] if r["part"].startswith("s_") else "other"].append(r)
print("by row kind: " + "; ".join("%s n%d max_ratio_clear %.2f median clearM5M7 %d um" % (k, len(v), max(x["ratio_clear"] for x in v), int(np.median([x["clear_M5M7_um"] for x in v]))) for k, v in sorted(by.items())))
# fW/fE columns: partitions outside the slice band
xs = [p["origin_um"][0] for n, p in PA.items() if n.startswith("s_")]; lo, hi = min(xs), max(xs) + 1442.88
side = [n for n, p in PA.items() if p["origin_um"][0] + T[p["type"]]["outline_um"][0] <= lo or p["origin_um"][0] >= hi]
sb = sum(int(s["width"]) for n in side for s in T[PA[n]["type"]].get("ft_slots") or [] if {s["in_face"], s["out_face"]} == {"N", "S"})
print("slice band x %.0f-%.0f um; %d partitions outside it carry %d N-S FT bits" % (lo, hi, len(side), sb))

print('== 3. horizontal capacity')

LH = {"M4": 1 / 0.048, "M6": 1 / 0.064}
into = {(pr["dst"]["part"], pr["dst"]["bus"]): pr for pr in d["ports"]}; outof = {(pr["src"]["part"], pr["src"]["bus"]): pr for pr in d["ports"]}
R = []
for n, p in PA.items():
    t = T[p["type"]]; w, h = t["outline_um"]; ew = turn = lat = 0
    for s in t.get("ft_slots") or []:
        i, o = into.get((n, s["name"] + "_i")), outof.get((n, s["name"] + "_o"))
        if not (i and o): continue
        fs = {s["in_face"], s["out_face"]}; W = int(s["width"])
        if fs == {"E", "W"}: ew += W
        elif fs == {"N", "S"}:
            if abs(sum(i["window_um"]) - sum(o["window_um"])) / 2 > 50: lat += W
        else: turn += W
    if ew + turn + lat == 0: continue
    blk = {L: np.zeros(int(np.ceil(h)), bool) for L in LH}
    for c in t.get("hard_cores") or []:
        y0 = c["origin_um"][1]; ch = c["outline_um"][1]; ob = ORD.get(lef_top(c.get("lef")), 5)
        for L in LH:
            if ob >= ORD[L]: blk[L][int(y0):int(y0 + ch + 1)] = True
    cap = sum((~blk[L]).sum() * v for L, v in LH.items()) * SH
    R.append(((ew + turn) / cap, (ew + turn + lat) / cap, n, p["type"], ew, turn, lat, int(cap)))
R.sort(reverse=True)
print("H bound: %d partitions; ideal (EW+turn) >0.55: %d, >1.0: %d; with current N-S lateral jogs >1.0: %d" % (len(R), sum(r[0] > .55 for r in R), sum(r[0] > 1 for r in R), sum(r[1] > 1 for r in R)))
for r in R[:12]: print("  ideal %.2f with-lateral %.2f %-11s %-28s ew %5d turn %5d lat %5d capH %d" % r[:2] + r[2:4] + r[4:] if False else "  ideal %.2f with-lat %.2f %-11s %-28s ew %5d turn %5d lat %5d capH %d" % r)
