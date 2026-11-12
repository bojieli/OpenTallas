import json, sys, collections
D = sys.argv[1]; K = float(sys.argv[2]) if len(sys.argv) > 2 else 0.72
CAP = float(sys.argv[3]) if len(sys.argv) > 3 else 1e9
calls = json.load(open(D + "/pairdump.json"))
print("calls", [(c["window"], c["n_pairs"], len(c["agg"]), len(c["over"])) for c in calls])
# calls order: TT then FF
cor = {}
for name, c in zip(("TT", "FF"), calls[:2]):
    cor[name] = c
import os
MARGIN=float(os.environ.get("MARGIN","0"))
W = {n: c["window"] for n, c in cor.items()}
WC = {n: c["window"]-MARGIN for n, c in cor.items()}
scale = {"TT": 1.0, "FF": K}
parts = set()
rows = {n: [] for n in cor}
for n, c in cor.items():
    for pa, pb, P, Q, cnt, tag in c["agg"]:
        parts.add(pa); parts.add(pb)
        rows[n].append((pa, pb, P, Q, cnt))
parts = sorted(p for p in parts if p)
# constraints d_A >= d_B + L ; d_B >= d_A - U   (all in TT ps; FF offsets = K * d)
LB = collections.defaultdict(lambda: -1e9)    # key (A,B): d_A - d_B >= L
UB = collections.defaultdict(lambda: 1e9)     # key (A,B): d_A - d_B <= U
infeasible = set()
for n in cor:
    s = scale[n]
    for pa, pb, P, Q, cnt in rows[n]:
        if pa == pb or pa is None or pb is None: continue
        lo = (Q - WC[n]) / s       # d_A - d_B >= (Q-W)/s
        hi = (WC[n] - P) / s       # d_A - d_B <= (W-P)/s
        if pa <= pb:
            k = (pa, pb)
        else:
            k = (pb, pa); lo, hi = -hi, -lo
        LB[k] = max(LB[k], lo); UB[k] = min(UB[k], hi)
for k in LB:
    if LB[k] > UB[k] + 1e-6: infeasible.add(k)
# relax: d>=0, least solution; skip infeasible keys (intrinsic)
d = {p: 0.0 for p in parts}
edges = []
for k in set(LB) | set(UB):
    if k in infeasible: continue
    a, b = k
    if LB[k] > -1e8: edges.append((a, b, LB[k]))        # d_a >= d_b + L
    if UB[k] < 1e8: edges.append((b, a, -UB[k]))        # d_b >= d_a - U
it = 0
while it < len(parts) + 5:
    ch = False
    for a, b, L in edges:
        v = d[b] + L
        if v > d[a] + 1e-9:
            d[a] = v; ch = True
    it += 1
    if not ch: break
cyc = ch
cappedcount = sum(1 for p in parts if d[p] > CAP)
print("iterations", it, "positive_cycle", cyc, "infeasible_pairs", len(infeasible))
vals = sorted(d.values())
print("trim TT ps: max %.1f mean %.1f nz %d of %d p50 %.1f p90 %.1f" % (vals[-1], sum(vals) / len(vals), sum(1 for v in vals if v > 0.5), len(vals), vals[len(vals)//2], vals[int(len(vals)*.9)]))
# apply cap
if CAP < 1e8:
    for p in parts: d[p] = min(d[p], CAP)
# evaluate remaining
res = {}
for n in cor:
    s = scale[n]; w = W[n]
    bad_keys = 0; bad_pairs = 0; grp = collections.Counter(); base_keys = 0
    for pa, pb, P, Q, cnt in rows[n]:
        da = d.get(pa, 0.0) * s; db = d.get(pb, 0.0) * s
        if max(P, Q) > w: base_keys += 1
        if pa != pb and max(P + da - db, Q + db - da) > w: bad_keys += 1
        elif pa == pb and max(P, Q) > w: bad_keys += 1
    # tap-pair level among initially-over pairs
    after = 0
    for x, y, P, Q, pa, pb, tag in cor[n]["over"]:
        da = d.get(pa, 0.0) * s; db = d.get(pb, 0.0) * s
        if pa == pb: after += 1; continue
        if max(P + da - db, Q + db - da) > w: after += 1
    res[n] = dict(base_part_pairs_over=base_keys, after_part_pairs_over=bad_keys, over_tap_pairs_base=len(cor[n]["over"]), over_tap_pairs_after=after)
print(json.dumps(res))
json.dump(dict(trim_tt=d, k_ff=K, cap=CAP, infeasible=sorted([list(k) for k in infeasible]), res=res), open(D + "/trim_k%.2f_cap%d.json" % (K, int(min(CAP, 99999))), "w"))
# intrinsic pairs detail
print("intrinsic (infeasible) part pairs:", len(infeasible), sorted(infeasible)[:12])
