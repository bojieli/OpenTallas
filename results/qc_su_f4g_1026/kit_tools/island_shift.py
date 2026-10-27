#!/usr/bin/env python3
# F4G (c) MODEL-REFIT feed: per-island and per-leaf GRT->RCX clock-arrival shift from meas_ck.tsv pairs.
# usage: island_shift.py LABEL GRT_TT RCX_TT GRT_FF RCX_FF > out.json   (col3 = arrival max rise, col5 = min rise)
import sys, json, re, statistics as st
def load(fn):
    d = {}
    for l in open(fn):
        if l.startswith("#"): continue
        f = l.rstrip("\n").split("\t")
        m = re.fullmatch(r"ot_ms_(Q\d+)(\w*?)_clk", f[1])
        if not m: continue
        d[f[0]] = (m.group(1), m.group(1) + m.group(2), float(f[2]), float(f[4]))
    return d
lab, gT, rT, gF, rF = sys.argv[1:6]
out = {"label": lab, "files": sys.argv[2:6], "basis": "meas_ck.tcl GRT(5_1_grt_prehold, rc_cal) vs RCX(6_final.spef); TT late=max rise, FF early=min rise", "corners": {}}
for cn, g, r, col in (("TT_late", gT, rT, 2), ("FF_early", gF, rF, 3)):
    G, R = load(g), load(r); common = sorted(set(G) & set(R))
    isl, leaf = {}, {}
    for p in common:
        i, lf = G[p][0], G[p][1]
        isl.setdefault(i, []).append((G[p][col], R[p][col])); leaf.setdefault(lf, []).append((G[p][col], R[p][col]))
    def summ(v): return {"n": len(v), "grt": round(st.mean(a for a, b in v), 2), "rcx": round(st.mean(b for a, b in v), 2), "shift": round(st.mean(b - a for a, b in v), 2)}
    I = {k: summ(v) for k, v in sorted(isl.items())}; L = {k: summ(v) for k, v in sorted(leaf.items())}
    lg = [v["grt"] for v in L.values()]; lr = [v["rcx"] for v in L.values()]
    out["corners"][cn] = {"sinks": len(common), "islands": I, "leaf_window_grt": round(max(lg) - min(lg), 2), "leaf_window_rcx": round(max(lr) - min(lr), 2),
                          "shift_range": [min(v["shift"] for v in I.values()), max(v["shift"] for v in I.values())], "leaves": L}
print(json.dumps(out, indent=1))
for cn, c in out["corners"].items():
    print("ISLAND_SHIFT %s %s win grt %.2f rcx %.2f :: %s" % (lab, cn, c["leaf_window_grt"], c["leaf_window_rcx"], " ".join("%s %+.1f" % (k, v["shift"]) for k, v in c["islands"].items())), file=sys.stderr)
