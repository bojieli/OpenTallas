import sys, json, time
sys.path.insert(0, "/wt/tools/die_plan")
import die_trial as DT, schema as S
P = S.Plan(S.load("/o/plan_s5.json"))
site = DT.SiteMap(P)
t = json.load(open("/o/kit_C/clock/tree.json"))["nodes"]
# vertical profile at a few x across lk_ES0 / ES1
for x in (23337.3, 23400, 24000, 24639.4, 25500, 26078.3, 26200):
    s = "".join({None: ".", "phy": "P", "core": "C", "outside": "o"}[site.why((x, y))] for y in range(0, 2400, 40))
    print("x %8.1f y0..2400/40: %s" % (x, s))
for i in ("778", "849"):
    d = t[i]; p = t[str(d["parent"])]
    a, b = (p["x"], p["y"]), (d["x"], d["y"])
    t0 = time.time(); poly = DT.legal_detour(site, a, b, step=5.4, margin=1500)
    print(i, "m1500", poly if poly is None or len(poly) < 12 else len(poly), round(time.time()-t0, 1))
for n, p in P.parts.items():
    if n in ("lk_ES0", "lk_ES1", "s_7S_x10"):
        print(n, p["origin_um"], P.types[p["type"]]["outline_um"])
