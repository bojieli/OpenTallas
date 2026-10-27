"""PATH-S81-PD13 (2) faster-upper-tree what-if (model only, UNCHECKED): scale every routed tree edge delay of level L
(rec node arrival - parent arrival) by f_L = model(variant, L) / model(base, L) from uptree_<C>.json, rebuild the
arrivals top-down (drivers + leaf-fed band roots), then run main kv_r18/mesh_mc18.py on the scaled rec (same seeds,
sigma, 0.21 %/mm gradient).  Tree geometry, mesh, stubs unchanged.
usage: whatif_fast.py REC UPTREE_JSON VARIANT CORNER SAMPLES OUT ROUTED QCDIR MC18 THEV"""
import json, re, runpy, sys
rec, up, var, C, ns, out, routed, qc, mc18, thev = sys.argv[1:11]
U = json.load(open(up)); base = {r["L"]: r["tot"] for r in U["base_4w_x24"]["levels"]}
new = {r["L"]: r["tot"] for r in U[var]["levels"]}; f = {L: new[L] / base[L] for L in base}
R = json.load(open(rec)); by = {n["tag"]: n for n in R["nodes"]}
def level(n):
    m = re.match(r"ckm_[nr](\d+)", n["cell"])
    return int(m.group(1)) if m else 12          # drivers 'i_j' sit at the end of the L12 leaf leg
old = {n["tag"]: n["arr"][C] for n in R["nodes"]}
for n in sorted(R["nodes"], key=lambda n: len(n["tag"])):
    if n["parent"] is None: continue
    L = level(n); n["arr"][C] = by[n["parent"]]["arr"][C] + f.get(L, 1.0) * (old[n["tag"]] - old[n["parent"]])
for b in R["band"]:
    p = by[b["parent"]]; b["arr"][C] = p["arr"][C] + (b["arr"][C] - old[p["tag"]])
drv = [n["arr"][C] for n in R["nodes"] if n["driver"]]
print(json.dumps(dict(variant=var, corner=C, factors={L: round(v, 3) for L, v in f.items()},
                      driver_arr_old=[round(min(old[n["tag"]] for n in R["nodes"] if n["driver"])), round(max(old[n["tag"]] for n in R["nodes"] if n["driver"]))],
                      driver_arr_new=[round(min(drv)), round(max(drv))])), flush=True)
json.dump(R, open(out + ".rec.json", "w"))
sys.argv = [mc18, out + ".rec.json", "--thev", thev, "--corner", C, "--samples", ns, "--routed", routed, "--out", out, "--qc", qc]
runpy.run_path(mc18, run_name="__main__")
