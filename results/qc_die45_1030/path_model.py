#!/usr/bin/env python3
"""DIE-QC-45 estimate-before-build: does the region DME stage model explain the routed in-region tap spread?
Per DME region: per plain tap (no __clk_c early core tap), sum over its region legs (region root -> tap node) of
  measured leg delay (routed early N rows), old model (tree was built with), refit model (refit_trial1.json);
spread = max - min over the region's plain taps.  If refit-predicted spread ~ measured spread, a DME rebuild with the
refit model removes it (residual ~ fit error); if not, the spread is not a stage-model error.
usage (from tools/die_plan on PYTHONPATH): path_model.py TREE ARR_EARLY_TXT BUILT_CAL REFIT_CAL CORNER OUT [--placed]"""
import sys, json, collections
import fit_dme_stage_cal as F
tree_f, arr_f, built_f, refit_f, C, out = sys.argv[1:7]; placed = "--placed" in sys.argv
T = json.load(open(tree_f)); arr = F.read_node_early(arr_f)
key = "leg" if C == "TT" else "leg_" + C
bc = json.load(open(built_f)); rc = json.load(open(refit_f)); cb = bc.get(key, bc["leg"]); cr = rc.get(key, rc["leg"])
rows = {i: (x, m) for i, x, m, _ in F.leg_rows(T, arr, 250.0, False, placed)}
nodes = {int(k): v for k, v in T["nodes"].items()}
def region(i):
    while i is not None:
        if nodes[i].get("region_root"): return nodes[i]["region_root"], i
        i = nodes[i]["parent"]
    return None, None
R = collections.defaultdict(list); miss = 0
for t in T["taps"]:
    if "__clk_c" in t["port"]: continue
    rn, ri = region(t["node"])
    if rn is None: continue
    i = t["node"]; s = [0.0, 0.0, 0.0]; ok = True; n = 0
    while i != ri:
        if i in rows:
            x, m = rows[i]; s[0] += m; s[1] += F.model_ps(x, cb); s[2] += F.model_ps(x, cr); n += 1
        else:
            nb = T["node_buf"]; a, b = arr.get(nb[str(i)]), arr.get(nb[str(nodes[i]["parent"])])
            if a is None or b is None: ok = False; break
            s[0] += a - b; s[1] += a - b; s[2] += a - b   # non-DME leg: measured on all three (not modelled)
        i = nodes[i]["parent"]
    if not ok: miss += 1; continue
    R[rn].append(s)
res = []
for rn, L in R.items():
    sp = [max(v[k] for v in L) - min(v[k] for v in L) for k in range(3)]
    # residual after a perfect refit rebuild ~ spread of (measured - refit) over taps
    resid = max(v[0] - v[2] for v in L) - min(v[0] - v[2] for v in L)
    res.append(dict(region=rn, taps=len(L), measured=round(sp[0], 1), old_model=round(sp[1], 1), refit_model=round(sp[2], 1), measured_minus_refit=round(resid, 1)))
res.sort(key=lambda r: -r["measured"])
summ = dict(corner=C, placed_stages=placed, regions=len(res), missing_taps=miss,
            measured_gt150=sum(r["measured"] > 150 for r in res), refit_resid_gt150=sum(r["measured_minus_refit"] > 150 for r in res),
            refit_resid_max=max(r["measured_minus_refit"] for r in res), worst=res[:8])
json.dump(dict(summary=summ, regions=res), open(out, "w"), indent=1); print(json.dumps(summ, indent=1))
