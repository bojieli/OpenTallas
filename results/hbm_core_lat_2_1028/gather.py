# HBM-CORE-LAT-2: per HBM hard-core module, every available clock-insertion source (C20h plan).
import json, os, re, sys, collections
PLAN, WT, B2L, R4, OUT = sys.argv[1:6]
p = json.load(open(PLAN)); cnt = collections.Counter(x["type"] for x in p["partitions"])
mods = {}
for tn, v in p["partition_types"].items():
    insts = {h["inst"]: h for h in v.get("hard_cores", [])}
    for t in v.get("clock", {}).get("taps", []):
        if t.get("kind") != "core": continue
        nm = t["name"]; hit = None
        for i in sorted(insts, key=len, reverse=True):
            if nm == i or nm.startswith(i + "."): hit = i; break
        h = insts[hit]; m = mods.setdefault(h["module"], dict(module=h["module"], placements=0, types=set(), lib=h.get("lib"),
                     outline=h.get("outline_um"), entries=set()))
        m["placements"] += cnt[tn]; m["types"].add(tn)
        ox, oy = h["origin_um"]; m["entries"].add((round(t["xy"][0]-ox, 2), round(t["xy"][1]-oy, 2)))
def etm(lib):
    out = {}
    for c, f in (("tt", lib), ("ff", lib.replace("_tt.lib", "_ff.lib"))):
        fp = os.path.join(WT, f)
        if not os.path.exists(fp): continue
        txt = open(fp).read(); tu = 1000.0 if re.search(r'time_unit\s*:\s*"1ns"', txt) else 1.0
        for kind in ("max_clock_tree_path", "min_clock_tree_path"):
            v = []
            for mm in re.finditer(r'timing_type\s*:\s*"?%s"?\s*;(.*?)\}\s*\}' % kind, txt, re.S):
                v += [float(x) for x in re.findall(r"[-+]?\d+\.\d+(?:e[-+]?\d+)?", mm.group(1).split("values", 1)[-1])]
            if v: out[f"{c}_{kind[:3]}"] = round((max(v) if kind[:3]=="max" else min(v)) * tu, 1)
    return out
b2l = collections.defaultdict(list)
for r in json.load(open(B2L))["views"]:
    if r.get("status") == "MEASURED": b2l[r["module"]].append(r)
r4 = {r["module"]: r for r in json.load(open(R4))["rows"]}
K, RCX, FFR = 0.8963, 0.9429, 0.7998
rows = []
for mod, m in sorted(mods.items(), key=lambda kv: -kv[1]["placements"]):
    w, h = m["outline"]; ent = sorted(m["entries"])
    Lmax = max(max(abs(ex - cx) + abs(ey - cy) for cx in (0, w) for cy in (0, h)) for ex, ey in ent)
    r = dict(module=mod, placements=m["placements"], types=sorted(m["types"]), outline=[round(w,2), round(h,2)], entries=ent,
             Lmax_um=round(Lmax, 1), r4_formula_tt=round(RCX*K*Lmax, 1), r4_formula_ff=round(RCX*K*Lmax*FFR, 1),
             r4=dict((k, r4[mod].get(k)) for k in ("cls", "model_centre_tt_ps", "model_centre_ff_ps", "measured_edge_entry_tt_ps", "farthest_um")) if mod in r4 else None,
             lib=m["lib"])
    if m["lib"]:
        r["etm"] = etm(m["lib"])
        ij = os.path.join(WT, os.path.dirname(m["lib"]), "insertion.json")
        if os.path.exists(ij):
            d = json.load(open(ij))
            r["insertion_json"] = dict(path=os.path.relpath(ij, WT), parasitics=d.get("parasitics"), db=d.get("db"), clock=d.get("clock"),
                **{c: dict(boundary=d[c]["boundary"], all=d[c]["all"]) for c in ("tt", "ff") if c in d},
                clock_measurements=sorted(d.get("clock_measurements", {}).keys()) if d.get("clock_measurements") else None)
    # exact or family-proxy b2l
    fam = mod.split("__v")[0] if "__v" in mod else None
    cand = b2l.get(mod, []) or []
    r["b2l_exact"] = [dict(view=x["view"], outline=x["outline_um"], ports=x["ports"], mean=x["insertion_mean_ps"], max=x["insertion_max_ps"]) for x in cand]
    prox = []
    for k, xs in b2l.items():
        if k == mod: continue
        base = re.sub(r"(__v[0-9a-f]{6}|__canon_[0-9a-f]+|__idpin.*|__tailx.*|__terminal.*)$", "", mod)
        if base and (k.startswith(base) or base.startswith(k)) and len(base) > 12:
            prox += [dict(view=x["view"], outline=x["outline_um"], mean=x["insertion_mean_ps"], max=x["insertion_max_ps"],
                          minp=min(v["min_ps"] for v in x["ports"].values() if v["sinks"] > 1)) for x in xs]
    r["b2l_proxy"] = prox[:12]
    rows.append(r)
json.dump(rows, open(OUT, "w"), indent=1, default=list)
for r in rows:
    ij = r.get("insertion_json")
    print(f"{r['module'][:48]:48s} {r['placements']:4d} {str(r['outline']):22s} Lmax {r['Lmax_um']:7.1f} r4f {r['r4_formula_tt']:6.1f}",
          "IJ tt", ij and ij.get("tt",{}).get("boundary"), "ff", ij and ij.get("ff",{}).get("boundary"), "ETM", r.get("etm"),
          "B2L", [(x["mean"], x["max"], x["outline"]) for x in r["b2l_exact"]][:2], "PROX", [(x["view"][:40], x["mean"], x["minp"], x["max"], x["outline"]) for x in r["b2l_proxy"]][:3])
