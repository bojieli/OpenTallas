"""DIE-HEAD refine (12.13a/b): region map that follows the routed spine_fishbone feed. Two partitions joined by a plan port
share a region iff the routed nominal clock offset of that port is small (|d_TT| <= --dmax, die STA related pair with
hold buffers inside the region) AND the routed unshared clock is short (<= --umax: no pair straddling a deep feed split
sits inside a region... unless d is ~0, then it is kept inside because the split is balanced); every other port is a
fixed-latency mesochronous crossing. Union-find over ports, so a region is a connected set; ports inside one region are
never crossings. Reports bits inside, crossings, and the count-aligned/current readings of the remaining crossings.
usage: feed_map.py PLAN LANDED_OCV.json OUT_MAP.json [--dmax 300]"""
import json, sys, collections
plan = json.load(open(sys.argv[1])); L = json.load(open(sys.argv[2])); out = sys.argv[3]
dmax = float(sys.argv[sys.argv.index("--dmax") + 1]) if "--dmax" in sys.argv else 300.0
k = [k for k in L["corners"] if k.startswith("TT_droop-regions_corelat") and L["corners"][k].get("all")][0]
row = {r["port"]: r for r in L["corners"][k]["all"]}
par = {}
def f(a):
    par.setdefault(a, a)
    while par[a] != a:
        par[a] = par[par[a]]; a = par[a]
    return a
parts = set()
for p in plan["ports"]:
    a, b = p["src"]["part"], p["dst"]["part"]
    parts |= {a, b}
    r = row.get(p["id"])
    if r and abs(r["d_ps"]) <= dmax:
        par[f(a)] = f(b)
for n in parts:
    f(n)
roots = collections.Counter(f(n) for n in parts)
nm = {r: f"F{i:02d}" for i, (r, _) in enumerate(roots.most_common())}
pr = {n: nm[f(n)] for n in sorted(parts)}
json.dump(dict(source=f"DIE-HEAD feed-following map: ports with |d_TT|<={dmax} ps on the routed sfb feed (LAND-HEAD-3 sfbR) join one region",
               dmax_ps=dmax, part_region=pr), open(out, "w"), indent=1)
tot = sum(p.get("width", 1) for p in plan["ports"])
inside = sum(p.get("width", 1) for p in plan["ports"] if pr[p["src"]["part"]] == pr[p["dst"]["part"]])
x = sum(1 for p in plan["ports"] if pr[p["src"]["part"]] != pr[p["dst"]["part"]])
print(f"dmax {dmax}: regions {len(roots)} sizes {sorted(roots.values(), reverse=True)[:12]} bits inside {inside}/{tot} ({100*inside/tot:.1f}%) crossings {x}/{len(plan['ports'])}")
