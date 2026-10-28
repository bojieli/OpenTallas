#!/usr/bin/env python3
"""DIE-QC: count-aligned evaluation of QC slice crossings. Remaps landed_phase_ocv partition endpoints to clock
regions (regions.json part_region), runs count_align_plan.plan (main MESO-COUNT-1 tool, unchanged), and reports
per-crossing K/DEPTH/latency + margins vs the COORD 20:35 window [(0.5T+ap), (DEPTH-0.5)T-ap].
usage: ca_qc.py LPO_JSON REGIONS_JSON CAP_DIR OUT_PREFIX"""
import json, sys, importlib.util, collections
lpo, regj, capdir, outp = sys.argv[1:5]
spec = importlib.util.spec_from_file_location("cap", capdir + "/count_align_plan.py")
cap = importlib.util.module_from_spec(spec); spec.loader.exec_module(cap)
T, AP = 833.0, 833.0 / 8
pr = json.load(open(regj))["part_region"]
d = json.load(open(lpo))
cs = ["TT_droop-regions_corelat250", "FF_droop-regions_corelat202.5"]
rows = [dict(r) for r in d["corners"][cs[0]]["all"]]
other = {r["port"]: r for r in d["corners"][cs[1]]["all"]}
for r in rows:  # union over TT/FF, identical to count_align_plan.main
    o = other[r["port"]]
    lo = min(r["d_ps"] - r["p_dn_ps"], o["d_ps"] - o["p_dn_ps"]); hi = max(r["d_ps"] + r["p_up_ps"], o["d_ps"] + o["p_up_ps"])
    r["p_dn_ps"], r["p_up_ps"] = r["d_ps"] - lo, hi - r["d_ps"]
    r["margin_ps"] = min(r["margin_ps"], o["margin_ps"])
    for k in ("unshared_a_ps", "unshared_b_ps"):
        r[k] = max(r.get(k, 0.0), o.get(k, 0.0))
    r["src_part"], r["dst_part"] = r["src"], r["dst"]
    r["src"], r["dst"] = pr[r["src"]], pr[r["dst"]]
summ, out = cap.plan(rows, T, AP, 0.05)
byp = {r["port"]: r for r in rows}
res = []
for o in out:
    r = byp[o["port"]]
    D = o["depth"]
    mlo = o["L_lo_ps"] - 0.5 * T  # distance from the ring's hard edge (0.5T), includes ap
    mhi = ((D - 0.5) * T - o["L_hi_ps"]) if D else None
    res.append(dict(o, src_part=r["src_part"], dst_part=r["dst_part"], unshared_ps=max(r["unshared_a_ps"], r["unshared_b_ps"]),
                    K=(o["lat_cycles"] - 1) if o["lat_cycles"] else None, margin_lo_ps=round(mlo, 1),
                    margin_hi_ps=round(mhi, 1) if mhi is not None else None,
                    margin_lo_beyond_ap_ps=round(mlo - AP, 1), margin_hi_beyond_ap_ps=round(mhi - AP, 1) if mhi is not None else None))
ok = [x for x in res if x["depth"]]
summ.update(source=lpo, aperture_ps=AP, period_ps=T,
            worst_margin_lo_ps=min(x["margin_lo_ps"] for x in ok) if ok else None,
            worst_margin_hi_ps=min(x["margin_hi_ps"] for x in ok) if ok else None,
            under100_both=sum(1 for x in ok if min(x["margin_lo_ps"], x["margin_hi_ps"]) < 100) + summ["fail"],
            K_hist=dict(collections.Counter(str(x["K"]) for x in res)), depth_hist=dict(collections.Counter(str(x["depth"]) for x in res)),
            max_derated_spread_ps=round(max(x["p_up_ps"] + x["p_dn_ps"] for x in res), 1),
            worst_old_ring_margin_ps=min(x["old_ring_margin_ps"] for x in res),
            old_ring_under100=sum(1 for x in res if x["old_ring_margin_ps"] < 100))
pairs = collections.defaultdict(list)
for x in res:
    pairs[tuple(sorted((x["src"], x["dst"])))].append(x)
summ["per_pair"] = {f"{a}|{b}": dict(n=len(v), d_range=[min(x["d_ps"] for x in v), max(x["d_ps"] for x in v)],
                                     max_spread=round(max(x["p_up_ps"] + x["p_dn_ps"] for x in v), 1),
                                     depth=sorted({str(x["depth"]) for x in v}), K=sorted({str(x["K"]) for x in v}),
                                     min_lo=min(x["margin_lo_ps"] for x in v),
                                     min_hi=min((x["margin_hi_ps"] for x in v if x["margin_hi_ps"] is not None), default=None),
                                     old_ring_min=min(x["old_ring_margin_ps"] for x in v)) for (a, b), v in sorted(pairs.items())}
json.dump(dict(summary=summ, crossings=res), open(outp + ".json", "w"), indent=0)
with open(outp + ".tsv", "w") as f:
    cols = ["port", "src_part", "dst_part", "src", "dst", "kind", "d_ps", "p_up_ps", "p_dn_ps", "unshared_ps", "L_lo_ps", "L_hi_ps",
            "K", "depth", "lat_cycles", "margin_lo_ps", "margin_hi_ps", "old_ring_margin_ps"]
    f.write("\t".join(cols) + "\n")
    for x in res:
        f.write("\t".join(str(x[c]) for c in cols) + "\n")
s = dict(summ); s.pop("per_pair")
print(json.dumps(s, indent=1))
for k, v in summ["per_pair"].items():
    print(k, v)
