#!/usr/bin/env python3
"""DIE-QC-5 independent NUMBER-CHECK: per clock region (droop_regions.json) and per partition, nominal tap spread
(max late - min late) and worst pair damage late(capture)-early(launch) without CPPR, from the proof tap arrivals.
usage: indep_skew.py PROOF_DIR"""
import json, sys, collections
pd = sys.argv[1]
reg = json.load(open(pd + "/droop_regions.json"))
for c in ("TT", "FF"):
    d = json.load(open(f"{pd}/tap_arrivals_{c}.json"))
    by_r, by_p = collections.defaultdict(list), collections.defaultdict(list)
    for t in d["taps"]:
        by_r[reg[t["port"]]].append(t); by_p[t["part"]].append(t)
    def spread(g):
        return max(t["late_ps"] for t in g) - min(t["late_ps"] for t in g)
    rs = sorted(((spread(g), r) for r, g in by_r.items()), reverse=True)
    ps = sorted(((spread(g), p) for p, g in by_p.items()), reverse=True)
    cls = collections.defaultdict(list)
    for s, r in rs:
        n = r.split(":", 1)[1]
        k = "c_*" if n.startswith("c_") else ("sl_*_su_c" if n.endswith("su_c") else ("sl_*" if n.startswith("sl_") else "other"))
        cls[k].append(s)
    print(c, "regions", len(rs), "region nominal spread max %.2f (%s)" % rs[0], "part max %.2f (%s)" % ps[0],
          "n>150", sum(s > 150 for s, _ in rs))
    for k, v in sorted(cls.items()):
        v.sort(); print("   class %-10s n %3d median %.1f max %.1f" % (k, len(v), v[len(v)//2], v[-1]))
