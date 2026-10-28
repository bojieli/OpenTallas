#!/usr/bin/env python3
"""start-tree ambiguity emulation (count_align_plan model): tree edge clean iff for rise (off 0) or fall (off T/2) the
interval [d_lo - ap, d_hi + ap] (TT u FF union of the STA d incl. OCV) holds no off + kT; an unclean edge adds n-1
cycles of path ambiguity to every crossing whose start-tree path uses it.  Crossing width = own d width + 2 wander +
amb T; D8 ok iff width <= (8-1)T - 2ap - 2*100 + T (one K step slack ignored: conservative lower = (D-2.25)T)."""
import json, sys, math, collections
cur = json.load(open(sys.argv[1])); bind = json.load(open(sys.argv[2])); key = sys.argv[3] if len(sys.argv) > 3 else "dsta"
T = 833.333; ap = T / 8
R = bind["regions"]; par = {r: v.get("parent") for r, v in R.items()}; tport = {r: v.get("tree_port") for r, v in R.items()}
ports = bind["ports"]
def iv(tag):
    lo = min(cur[key][c][tag][0] for c in ("TT", "FF") if tag in cur[key][c]); hi = max(cur[key][c][tag][1] for c in ("TT", "FF") if tag in cur[key][c]); return lo, hi
def nvals(lo, hi, off):
    return max(0, math.floor((hi - off) / T) - math.ceil((lo - off) / T) + 1)
amb = {}; widths = []
for r, p in par.items():
    if p is None: continue
    b = ports[tport[r]]; tag = f"{b['src']}->{b['dst']}"
    lo, hi = iv(tag); widths.append(hi - lo)
    n = min(nvals(lo - ap, hi + ap, 0.0), nvals(lo - ap, hi + ap, T / 2))
    amb[r] = max(0, n - 1) if n >= 1 else 0
    amb[r] = 1 if n >= 1 else 0  # n>=1 boundary inside -> J takes 2 values (1 cycle ambiguity)
ne = len(amb); clean = sum(1 for v in amb.values() if v == 0)
def lin(r):
    o = [r]
    while par.get(o[-1]) is not None: o.append(par[o[-1]])
    return o
wd = sorted(widths); print(f"[{key}] start-tree edges {ne}, clean {clean}; tree-edge d width (TTuFF incl OCV) ps med {wd[len(wd)//2]:.0f} p90 {wd[int(.9*len(wd))]:.0f} max {wd[-1]:.0f} (clean guaranteed <= {T/2-2*ap:.0f})")
reg_of = {p: v["region"] for p, v in bind["parts"].items() if isinstance(v, dict)}
A = collections.Counter(); need = collections.Counter(); hopsc = collections.Counter(); W = []
for pid, b in ports.items():
    s, d = b["src"], b["dst"]
    if s not in par or d not in par: continue
    ls, ld = lin(s), lin(d); L = next(x for x in ls if x in set(ld))
    path = ls[:ls.index(L)] + ld[:ld.index(L)]
    is_tree = any(tport.get(x) == pid for x in path) and len(path) == 1
    a = 0 if is_tree else sum(amb[x] for x in path)
    tag = f"{s}->{d}"
    if tag not in cur[key]["TT"]: continue
    lo, hi = iv(tag); w = (hi - lo) + 2 * float(b.get("wander_ps") or 0) + a * T
    W.append(w); A[min(a, 12)] += 1; hopsc[min(len(path), 20)] += 1
    need["D4" if w <= (4 - 2.25) * T - 200 + ap * 0 else "D8" if w <= (8 - 2.25) * T else "D16" if w <= (16 - 2.25) * T else ">D16"] += 1
print(f"[{key}] path ambiguity cycles hist {sorted(A.items())}; start-tree path hops {sorted(hopsc.items())}")
print(f"[{key}] depth needed (conservative, K quantisation worst): {dict(need)}")
