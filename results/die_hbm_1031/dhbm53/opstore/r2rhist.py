#!/usr/bin/env python3
"""r2rhist.py GEOM_RULES_DIR geom.tsv : r2r > 405 captures grouped by launch / capture name prefix (read-only analysis)."""
import sys, inspect, re, collections
sys.path.insert(0, sys.argv[1]); import geom_rules as G
src = inspect.getsource(G.r2r_metrics)
src = src.replace("def r2r_metrics(D):", "def r2r_hist(D):").replace(
    "        if mx > R2R_MAX:\n            n_gt += 1", "        if mx > R2R_MAX:\n            n_gt += 1\n            OUTL.append((mx, src, cap))")
ns = dict(G.__dict__); OUTL = []; ns["OUTL"] = OUTL
exec(src, ns)
D = G.Design(sys.argv[2])
r = ns["r2r_hist"](D)
name = lambda i: D.cells[i][6] if i in D.cells else str(i)
def pre(n, k=6):
    n = re.sub(r"\\\[\d+\\\]|\[\d+\]", "[*]", n); n = re.sub(r"_\d+_$", "_N_", n)
    return "/".join(n.split("/")[:2])[:110]
print({k: r[k] for k in ("r2r_max", "r2r_captures_gt405", "r2r_captures")})
L = collections.Counter(pre(name(s)) for _, s, _ in OUTL); C = collections.Counter(pre(name(c)) for _, _, c in OUTL)
print("distinct launch regs", len({s for _, s, _ in OUTL}))
print("TOP LAUNCH"); [print(f"  {v:6d} {k}") for k, v in L.most_common(12)]
print("TOP CAPTURE"); [print(f"  {v:6d} {k}") for k, v in C.most_common(12)]
b = collections.Counter(int(m // 100) * 100 for m, _, _ in OUTL); print("dist hist", sorted(b.items()))
