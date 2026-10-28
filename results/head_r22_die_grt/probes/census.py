import json, sys, collections
sys.path.insert(0, sys.argv[1])
import schema as S, die_clock_128 as C, die_infra as DI, die_clock_mesh as D
O, plan = sys.argv[2], sys.argv[3]
M = json.load(open(O + "/clk/mesh.json"))
spec = json.load(open(O + "/clk/mesh_spec.json"))
P = S.Plan(S.load(plan)); pgr = DI.pg_rects(P, C.pg_grid(P, None))
nd = D.NDR[M["meta"]["ndr"]]
wires = M["fixed_wires"]
msegs = D.mesh_segments(M) + C.tree_segs(wires)
cen = C.metal_census(C.pg_shapes(pgr) + C.clock_shapes(msegs, nd, "VSS"), nd["space"], limit=10**7)
strapsH = {round(h["y"], 3) for h in spec["M8"]}; strapsV = {round(v["x"], 3) for v in spec["M9"]}
c = collections.Counter(); bad_y = collections.Counter()
for r in cen["rows"]:
    a, b = (r["a"], r["b"]) if r["a"][2] != "pg" else (r["b"], r["a"])
    if a[2] == "pg": continue
    L = a[0]
    if L == "M8":
        cy = round((a[3] + a[4]) / 2, 3); on_strap = any(abs(cy - y) < 1.0 for y in strapsH); ln = abs(a[6] - a[5])
    else:
        cy = round((a[3] + a[4]) / 2, 3); on_strap = any(abs(cy - x) < 1.0 for x in strapsV); ln = abs(a[6] - a[5])
    kind = "strap" if on_strap and ln > 200 else ("jog<=100" if ln <= 100 else "other")
    c[(r["what"], a[2], a[1][:16], L, kind, b[1])] += 1
for k, v in c.most_common(30): print(v, k)
print("shorts", cen["shorts"], "spacing", cen["spacing"])
