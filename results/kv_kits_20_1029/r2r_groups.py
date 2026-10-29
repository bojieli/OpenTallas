# KV-KITS-20 diagnostic: per-capture r2r (same exact u/v propagation as geom_rules.r2r_metrics), grouped by src/cap name stem
import sys, re, json, inspect
from collections import Counter, defaultdict
sys.path.insert(0, sys.argv[1]); import geom_rules as G
D = G.Design(sys.argv[2])
src = inspect.getsource(G.r2r_metrics)
src = src.replace("def r2r_metrics(D):", "def r2r_all(D):")
src = src.replace("        if mx > R2R_MAX:\n            n_gt += 1", "        if mx > R2R_MAX:\n            n_gt += 1\n            OUT.append((mx, src, cap))")
OUT = []
ns = dict(G.__dict__); ns["OUT"] = OUT
exec(src, ns); ns["r2r_all"](D)
stem = lambda s: re.sub(r"\\\\\[\d+\\\\\]", "[]", re.sub(r"\$_DFF.*", "", s))
nm = lambda i: D.cells[i][6]
xy = lambda i: tuple(round(v,1) for v in G.ctr(D.cells[i]))
pairs = Counter(); srcs = Counter(); caps = Counter(); ex = {}
for mx, s, c in OUT:
    k = (stem(nm(s)), stem(nm(c))); pairs[k] += 1; srcs[k[0]] += 1; caps[k[1]] += 1
    if k not in ex or mx > ex[k][0]: ex[k] = (round(mx,1), xy(s), xy(c))
print("violators", len(OUT))
for k, n in pairs.most_common(25): print(n, k[0], "->", k[1], ex[k])
print("-- src stems"); [print(n, k) for k, n in srcs.most_common(12)]
print("-- cap stems"); [print(n, k) for k, n in caps.most_common(12)]
# distinct source flops per stem + their positions spread
sf = defaultdict(set)
for mx, s, c in OUT: sf[stem(nm(s))].add(s)
for k in list(srcs)[:8]:
    pts = [xy(i) for i in sf[k]]; print("SRCSTEM", k, len(pts), "x", min(p[0] for p in pts), max(p[0] for p in pts), "y", min(p[1] for p in pts), max(p[1] for p in pts))
cf = defaultdict(list)
for mx, s, c in OUT: cf[stem(nm(s))].append((xy(c), mx, stem(nm(c))))
for k, L in sorted(cf.items(), key=lambda t: -len(t[1]))[:4]:
    xs=[p[0][0] for p in L]; ys=[p[0][1] for p in L]
    face=Counter(G.face_of(p[0][0],p[0][1],D.die,tol=8.0) for p in L)
    cs=Counter(re.sub(r"\[\]$","",p[2]).split(".")[-1] for p in L)
    print("CAPS of", k, len(L), "x", min(xs), max(xs), "y", min(ys), max(ys), "faces", dict(face), "dist", round(min(p[1] for p in L)), round(max(p[1] for p in L)), cs.most_common(6))
