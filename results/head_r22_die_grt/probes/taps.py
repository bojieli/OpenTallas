import json, sys, collections, bisect
sys.path.insert(0, sys.argv[1])
import schema as S, die_clock_128 as C, die_infra as DI
O, plan = sys.argv[2], sys.argv[3]
M = json.load(open(O + "/clk/mesh.json"))
P = S.Plan(S.load(plan)); pgr = DI.pg_rects(P, C.pg_grid(P, None))
# per layer: list of (lo, hi, along_lo, along_hi, net) in the cross coordinate
st = {"M8": [], "M9": []}
for net, L, x0, y0, x1, y1 in [r[:6] for r in pgr]:
    if L == "M8": st[L].append((y0, y1, x0, x1, net))
    elif L == "M9": st[L].append((x0, x1, y0, y1, net))
def blocked(L, c, a, hw, sp=0.08):
    for lo, hi, alo, ahi, net in st[L]:
        if lo - sp - hw < c < hi + sp + hw and alo <= a <= ahi: return net
    return None
for L in st: st[L].sort()
cnt = collections.Counter(); kinds = collections.Counter()
for t in M["taps"]:
    mb = t["mesh_boundary"]; x, y = t["xy"]; L = t["layer"]
    j = mb.get("jog_um", 0)
    b8 = blocked("M8", y, x, 0.16); b9 = blocked("M9", x, y, 0.16)
    kinds[mb.get("endpoint_kind")] += 1
    cnt[(mb.get("endpoint_kind"), "jog" if j > 1e-6 else "on-strap", L, "M8pad-blocked" if b8 else "M8pad-free", "M9-blocked" if b9 else "M9-free")] += 1
for k, v in sorted(cnt.items()): print(v, k)
print(kinds)
spec = json.load(open(O + "/clk/mesh_spec.json"))
H = [(h["y"], h["x0"], h["x1"]) for h in spec["M8"]]; V = [(v["x"], v["y0"], v["y1"]) for v in spec["M9"]]
res = collections.Counter(); exA = []
for t in M["taps"]:
    x, y = t["xy"]; k = t["mesh_boundary"]["endpoint_kind"]
    dV = min([abs(xx - x) for xx, y0, y1 in V if y0 <= y <= y1] or [1e9])   # M8 jog to an M9 strap
    dH = min([abs(yy - y) for yy, x0, x1 in H if x0 <= x <= x1] or [1e9])   # M9 jog to an M8 strap
    ok8 = not blocked("M8", y, x, 0.16) and dV <= 450
    ok9 = not blocked("M9", x, y, 0.16) and not blocked("M8", y, x, 0.16) and dH <= 450
    res[(k, "M8jog-legal" if ok8 else ("M9jog-legal" if ok9 else "needs-endpoint-move"))] += 1
for k_, v_ in sorted(res.items()): print(v_, k_)
parts = {p["name"]: p["type"] for p in (S.load(plan)["partitions"] if isinstance(S.load(plan)["partitions"], list) else [dict(v, name=k) for k, v in S.load(plan)["partitions"].items()])}
ty = collections.Counter(); mod = collections.Counter()
for t in M["taps"]:
    x, y = t["xy"]
    if t["mesh_boundary"]["endpoint_kind"] == "published_grid_clock" and blocked("M8", y, x, 0.16):
        ty[parts.get(t["part"], "?")] += 1; mod[round(y % 4.32, 3)] += 1
print(ty.most_common()); print(mod.most_common(6))
