import sys, json, time
sys.path.insert(0, "/wt/tools/die_plan")
import die_trial as DT, schema as S
P = S.Plan(S.load("/o/plan_s5.json"))
site = DT.SiteMap(P)
t = json.load(open("/o/kit_C/clock/tree.json"))["nodes"]
for i in ("849", "778", "12129"):
    d = t[i]; p = t[str(d["parent"])]
    a, b = (p["x"], p["y"]), (d["x"], d["y"])
    print(i, "legal a", site.legal(a), site.why(a), "legal b", site.legal(b), site.why(b))
    for dx, dy in ((5.4,0),(-5.4,0),(0,5.4),(0,-5.4)):
        print("   b nb", dx, dy, site.why((b[0]+dx, b[1]+dy)), " a nb", site.why((a[0]+dx, a[1]+dy)))
    for st in (5.4, 2.16):
        t0 = time.time(); poly = DT.legal_detour(site, a, b, step=st)
        print("  step", st, "poly", None if poly is None else len(poly), round(time.time()-t0,1), "s")
    na, nb = site.nearest(a), site.nearest(b)
    print("  nearest", na, nb)
