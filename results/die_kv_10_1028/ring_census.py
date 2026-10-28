#!/usr/bin/env python3
"""DIE-KV-10 step 2: KV landing-ring (W,D) class census at W>=250 + pv kit cells (ESTIMATE, UNCHECKED-indep).
Inputs: DIE-KV-8 bind_s2 bind_clock_landings.json (3595 rings, one per CA port, ring in dst partition), RT20 event plan
(parts->type), DIE-KV-9 est_1216 (joint TT+FF OCV width), DIE-KV-9 pv_counts (kit cells with W>=1000 rings black-boxed),
DIE-KV-9 ring_area (measured abc cells of 8 classes -> linear cells(W,D) fit).
Scenarios: now = bound ring_depth; bound = D4 if (W(4)-width-T)/2 >= 100 else D8 (12.16 b(iii) on today's clock);
d4 = all D4 (local-form expectation)."""
import json, sys, collections, gzip
B, PLAN, EST, PVC, AREA, OUT = sys.argv[1:7]
L = json.load(open(B)); P = json.load(open(PLAN))
est = {r["port"]: r for r in json.load(gzip.open(EST))["rows"]}
pvc = json.load(open(PVC)); area = json.load(open(AREA))
T, ap = 833.333, 104.167
Wd = lambda D: (D - 1) * T - 2 * ap
# linear cell fit per depth from the measured classes
fit = {}
for D in (4, 8):
    pts = [(int(k[9:].split("d")[0]), v["cells"]) for k, v in area.items() if k.endswith(f"d{D}")]
    n = len(pts); mx = sum(x for x, _ in pts) / n; my = sum(y for _, y in pts) / n
    b = sum((x - mx) * (y - my) for x, y in pts) / sum((x - mx) ** 2 for x, _ in pts); fit[D] = (my - b * mx, b)
cells = lambda W, D: fit[D][0] + fit[D][1] * W
ptype = {p["name"]: p["type"] for p in P["partitions"]}
rings = []
for r in L["ports"]:
    e = est[r["port"]]
    dn = int(r["ring_depth"])
    db = 4 if (Wd(4) - e["width"] - T) / 2 >= 100 else 8
    rings.append(dict(port=r["port"], W=int(r["width"]), dst=r["dst"], type=ptype.get(r["dst"]), now=dn, bound=db, d4=4))
miss = [x for x in rings if x["type"] is None]
res = dict(fit_cells_per_ring={D: dict(a=round(a, 1), b_per_bit=round(b, 2)) for D, (a, b) in fit.items()},
           rings=len(rings), unmapped_dst=len(miss), scenarios={})
types_n = collections.Counter(ptype.values())
for sc in ("now", "bound", "d4"):
    out = {}
    for wmin in (1000, 500, 250):
        cls = collections.Counter((x["W"], x[sc]) for x in rings if x["W"] >= wmin)
        out[f"W>={wmin}"] = dict(classes=len(cls), instances=sum(cls.values()),
                                 depth_mix=dict(collections.Counter(f"D{d}" for (w, d) in cls.elements())))
    cls250 = collections.Counter((x["W"], x[sc]) for x in rings if x["W"] >= 250)
    out["classes_W>=250"] = sorted([dict(W=w, D=d, inst=n) for (w, d), n in cls250.items()], key=lambda z: (-z["inst"], z["W"]))
    # pv kits: kit cells at W>=250 hardened = DIE-KV-9 count (W>=1000 out, depths 'now') - soft rings 250<=W<1000 (now depth)
    # + depth delta on the remaining soft (<250) rings for this scenario
    kits = {}
    for t, v in pvc.items():
        parts = sorted(pn for pn, tt in ptype.items() if tt == t)
        if not parts:
            kits[t] = dict(error="no part"); continue
        mine = [x for x in rings if x["dst"] == parts[0]]
        mid = sum(cells(x["W"], x["now"]) for x in mine if 250 <= x["W"] < 1000)
        small_delta = sum(cells(x["W"], x[sc]) - cells(x["W"], x["now"]) for x in mine if x["W"] < 250)
        kits[t] = dict(instances=len(parts), cells_kv9_w1000=v["cells"], est_cells_w250=round(v["cells"] - mid + small_delta),
                       hard_rings_w250=sum(1 for x in mine if x["W"] >= 250), soft_rings_lt250=sum(1 for x in mine if x["W"] < 250))
    out["pv_kits"] = kits
    out["pv_max_w250"] = max(k["est_cells_w250"] for k in kits.values() if "est_cells_w250" in k)
    res["scenarios"][sc] = out
json.dump(res, open(OUT, "w"), indent=1)
for sc, o in res["scenarios"].items():
    print(sc, {k: (v["classes"], v["instances"], v["depth_mix"]) for k, v in o.items() if k.startswith("W>=")}, "pv_max", o["pv_max_w250"])
print("fit", res["fit_cells_per_ring"], "unmapped", res["unmapped_dst"])
