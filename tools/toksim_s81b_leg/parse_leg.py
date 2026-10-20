#!/usr/bin/env python3
"""TOKSIM-S81B/LEG (10-19): reduce a tb_leg_s81 run log to per-window start->retire cycles and check them against the
structural law of the release die: every ring link + the stop it enters = k_link + 5 edges (k = die.v landing strap),
constant for every beat of a window (static schedule: no beat waits).
usage: parse_leg.py <run.log[.gz]> <windows.json> <leg_chain_gen.json> <out.json>"""
import gzip, json, sys
from collections import defaultdict

log, wj, cj, oj = sys.argv[1:5]
op = gzip.open if log.endswith(".gz") else open
W = json.load(open(wj))["windows"]
links = json.load(open(cj))["links"]
lat = defaultdict(list); verdict = None; stats = None
for l in op(log, "rt"):
    if l.startswith("LB "):
        t, f, s, d, k, a, b = map(int, l.split()[1:])
        lat[(t, f, s, d)].append((k, b - a))
    elif l.startswith(("PASS leg_s81", "FAIL leg_s81")):
        verdict = l.strip()
    elif l.startswith("LEG_STATS"):
        stats = l.strip()


def law(tier, src, dst):
    t = "SN"[tier]; c0, c1 = min(src, dst), max(src, dst); d = "E" if dst > src else "W"
    return sum(links[f"xr{d}_{c}{t}_l0"]["k"] + 5 for c in range(c0, c1))


rows = []; law_bad = 0; nonconst = 0
for w in W:
    tier = "SN".index(w["tier"]); f = w["flow"]
    key = (tier, f, w["src_col"], w["dst_col"])
    v = [x for x in lat[key]]
    rows.append(None)
# group by window using the beat index order (windows are issued in order, one at a time)
idx = 0; out = []
for w in W:
    tier = "SN".index(w["tier"]); key = (tier, w["flow"], w["src_col"], w["dst_col"])
    seq = lat[key][:w["beats"]]; lat[key] = lat[key][w["beats"]:]
    vals = sorted(set(x for _, x in seq))
    L = law(tier, w["src_col"], w["dst_col"])
    ok = len(seq) == w["beats"] and vals == [L]
    law_bad += 0 if ok else 1
    nonconst += 0 if len(vals) == 1 else 1
    out.append(dict(w, cycles=vals[0] if len(vals) == 1 else vals, law=L, law_ok=ok, beats_seen=len(seq),
                    k_straps=[links[f"xr{'E' if w['dst_col'] > w['src_col'] else 'W'}_{c}{w['tier']}_l0"]["k"]
                              for c in range(min(w['src_col'], w['dst_col']), max(w['src_col'], w['dst_col']))]))
res = dict(verdict=verdict, stats=stats, windows=out, law_violations=law_bad, nonconstant_windows=nonconst,
           law="cycles = sum over the ring links of (k_link + 5) (die.v dsfd_dvland_276 strap k)",
           PASS=bool(verdict and verdict.startswith("PASS") and law_bad == 0))
json.dump(res, open(oj, "w"), indent=1)
print(verdict); print(stats); print("law violations", law_bad, "non-constant windows", nonconst, "PASS" if res["PASS"] else "FAIL")
