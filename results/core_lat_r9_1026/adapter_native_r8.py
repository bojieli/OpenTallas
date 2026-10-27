#!/usr/bin/env python3
"""R9 step 0b: on an R8-format plan record, compare the adapter net rule (seg to hub + Manhattan stubs / root fan)
with the native uf_phys rule (Steiner over driver+children x detour = maze seg / Manhattan).  Reports stub stats.
usage: adapter_native_r8.py PLAN.json.gz GEO LIBDIR FIT    PLAN MODEL, UNCHECKED."""
import gzip, json, statistics as st, sys, copy
from pathlib import Path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[0] / "core_lat_r8_1026"))
import l0r_r8_uf3 as A
U, V3 = A.U, A.V3
rj, geo, libdir, fit = sys.argv[1:5]
op = gzip.open if rj.endswith(".gz") else open
rec = json.load(op(rj, "rt"))[0]
F = json.load(open(fit)); pmax, pmin = dict(F["PMAX"]), dict(F["PMIN"])
for c in sorted({n[3] for n in rec["nodes_xy"]}):
    if c not in U.SIZES: U.SIZES.append(c)
L = U.load_libs(libdir)
AP = A.PlanFromRecord(rec, geo)
NP = copy.deepcopy(AP)
stubs, nm = [], 0
for d, ch in AP.kids.items():
    if len(ch) < 2: continue
    nm += 1
    net = AP.nets[d]
    stubs += [e[2] for e in net["edges"][1:]] if len(net["edges"]) > len(ch) else [e[2] for e in net["edges"]]
    dxy = AP.nodes[d]["xy"]
    P = [dxy] + [AP.nodes[c]["xy"] for c in ch]
    pts, E = U.steiner(P)
    seglen = sum(e[2] for e in net["edges"])
    mh = sum(e[2] for e in [(a, b, U.man(pts[a], pts[b])) for a, b in E])
    f = max(1.0, seglen / mh) if mh > 1 else 1.0
    NP.nets[d] = dict(pts=pts, edges=[(a, b, U.man(pts[a], pts[b]) * f) for a, b in E], pin={c: i + 1 for i, c in enumerate(ch)}, detour=f)
o = {}
for tag, plan in (("adapter", AP), ("native_rule", NP)):
    o[tag] = A.predict(plan, L, pmax, pmin)
print("multi-child nets", nm, "stub um mean %.2f max %.2f" % (st.mean(stubs), max(stubs)))
for tag in o:
    g = o[tag]; print(tag, "TT %.2f w%.2f FF %.2f w%.2f" % (g["TT_rise"]["mean"], g["TT_rise"]["window"], g["FF_early"]["mean"], g["FF_early"]["window"]))
if len(sys.argv) > 5:
    rows = []
    for d, ch in AP.kids.items():
        if len(ch) < 2: continue
        a, n = AP.nets[d], NP.nets[d]
        la = sum(e[2] for e in a["edges"]); ln = sum(e[2] for e in n["edges"])
        rows.append((round(ln - la, 1), d, len(ch), round(la, 1), round(ln, 1), round(n["detour"], 2), [AP.nodes[c]["kind"] for c in ch][:1]))
    rows.sort(reverse=True)
    for r in rows[:12]: print(r)
