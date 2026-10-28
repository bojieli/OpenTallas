# HBM-RISK-2 R3: core internal insertion vs plan tap latency per HBM hard-core type (C20h plan). ESTIMATE.
import json, re, os, sys, collections, glob
PLAN, WT, B2L, R4, OUT = sys.argv[1:6]
p = json.load(open(PLAN))
cnt = collections.Counter(x["type"] for x in p["partitions"])
mods = collections.defaultdict(lambda: dict(inst=0, lib=None, types=set()))
taps = collections.defaultdict(list)
for tn, v in p["partition_types"].items():
    for h in v.get("hard_cores", []):
        m = mods[h["module"]]; m["inst"] += cnt[tn]; m["types"].add(tn)
        if h.get("lib"): m["lib"] = h["lib"]
    for t in v.get("clock", {}).get("taps", []):
        if t.get("kind") == "core":
            taps[t.get("budget_owner")].append((t.get("insertion_ps"), t.get("insertion_ff_ps"), t.get("early_ps", 0)))
def lib_lat(path):
    out = {}
    for corner, f in (("tt", path), ("ff", path.replace("_tt.lib", "_ff.lib"))):
        fp = os.path.join(WT, f)
        if not os.path.exists(fp): continue
        txt = open(fp).read()
        vals = {}
        for kind in ("max_clock_tree_path", "min_clock_tree_path"):
            for mm in re.finditer(r'timing_type\s*:\s*"?%s"?\s*;(.*?)\}\s*\}' % kind, txt, re.S):
                nums = [float(x) for x in re.findall(r'[-+]?\d+\.\d+(?:e[-+]?\d+)?', mm.group(1).split("values", 1)[-1])]
                if nums: vals.setdefault(kind, []).append(max(nums))
        tu = 1000.0 if re.search(r'time_unit\s*:\s*"1ns"', txt) else 1.0
        out[corner] = {k: round(max(v) * tu, 1) for k, v in vals.items()}
    return out
b2l = {r["module"]: r for r in json.load(open(B2L))["views"]}
r4 = {r["module"]: r for r in json.load(open(R4))["rows"]}
rows = []
for mod, m in sorted(mods.items(), key=lambda kv: -kv[1]["inst"]):
    ll = lib_lat(m["lib"]) if m["lib"] else {}
    b = b2l.get(mod, {}); r = r4.get(mod, {})
    tp = taps.get(mod, [])
    tap_tt = sorted(set(t[0] for t in tp)); tap_ff = sorted(set(t[1] for t in tp)); early = sorted(set(t[2] for t in tp))
    # internal insertion basis, best available: lib ETM max (real view) > b2l measured natural > r4 model centre
    L_tt = L_ff = None; basis = "none"
    if ll.get("tt", {}).get("max_clock_tree_path"):
        L_tt = ll["tt"]["max_clock_tree_path"]; basis = "lib_etm_max"
        L_ff = ll.get("ff", {}).get("max_clock_tree_path") or round(L_tt * 0.81, 1)
    elif b.get("insertion_mean_ps"):
        L_tt = b["insertion_mean_ps"]; L_ff = round(L_tt * 0.81, 1); basis = "b2l_measured_natural"
    elif r.get("model_centre_tt_ps"):
        L_tt = r["model_centre_tt_ps"]; L_ff = r["model_centre_ff_ps"]; basis = "r4_model_centre"
    tt0 = tap_tt[0] if tap_tt else 250.0; ff0 = tap_ff[0] if tap_ff else 202.5
    d_ff = None if L_ff is None else round(L_ff - ff0 - (early[0] if early else 0), 1)
    # FF hold at core input boundary (parent zero-logic reg -> core pin reg): m0 = clk->q + short wire - hold ~ +25 ps (UNCHECKED);
    # minus core-late skew d_ff, minus unshared OCV on core-internal tree (AOCV 5% of L_ff, UNCHECKED)
    hold = None if d_ff is None else round(25.0 - d_ff - 0.05 * L_ff, 1)
    rows.append(dict(module=mod, inst=m["inst"], types=sorted(m["types"]), lib=bool(m["lib"]), basis=basis,
                     L_tt=L_tt, L_ff=L_ff, lib_lat=ll, b2l_status=b.get("status"), b2l_keys=sorted(b.keys())[:0],
                     r4_cls=r.get("cls"), r4_tt=r.get("model_centre_tt_ps"), tap_tt=tap_tt, tap_ff=tap_ff, early=early,
                     d_ff=d_ff, hold_ff_est=hold))
json.dump(rows, open(OUT, "w"), indent=1)
for r in rows:
    print(f'{r["module"][:52]:52s} {r["inst"]:4d} {r["basis"]:21s} Ltt {r["L_tt"]} Lff {r["L_ff"]} tap {r["tap_tt"]}/{r["tap_ff"]} e{r["early"]} dFF {r["d_ff"]} holdFF {r["hold_ff_est"]} r4 {r["r4_cls"]} {r["r4_tt"]}')
