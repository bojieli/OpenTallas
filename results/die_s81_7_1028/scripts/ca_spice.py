"""DIE-KV-4: CA plan (MESO-RECONCILE-1 count_align_plan, single convention) on measured landed_phase_ocv rows, region
# DIE-S81-7 copy of results/die_qc4_1028/scripts/ca_spice.py (DIE-KV-4 recipe), imports main tools/die_plan/count_align_plan
crossings only, clock-derived terms (d, p_up, p_dn, unshared) scaled PER CORNER by the spice factor (METHODOLOGY 12.15b:
TT x1.0485, FF x1.0552; x1.00 = unscaled).  ca_spice.py LPO REGIONS OUT_PREFIX SCALE_TT SCALE_FF [--mc N] [--pad P]"""
import json, sys, argparse, os
sys.path.insert(0, "/srv/opentallas-scratch2/claude/wt/die-s81-7/tools/die_plan")   # DIE-S81-7: main count_align_plan
import count_align_plan as CAP
a = argparse.ArgumentParser(); a.add_argument("lpo"); a.add_argument("regions"); a.add_argument("pre")
a.add_argument("stt", type=float); a.add_argument("sff", type=float); a.add_argument("--mc", type=int, default=2000)
a.add_argument("--pad", type=int, default=0)
a = a.parse_args()
reg = json.load(open(a.regions))["part_region"]
d = json.load(open(a.lpo))
keys = {"TT_droop-regions_corelat250": a.stt, "FF_droop-regions_corelat202.5": a.sff}
for k, S in keys.items():
    rows = []
    for r in d["corners"][k]["all"]:
        x, y = reg[r["src"]], reg[r["dst"]]
        if x == y:
            continue
        r = dict(r, src=x, dst=y, src_part=r["src"], dst_part=r["dst"])
        for f in ("d_ps", "p_up_ps", "p_dn_ps", "unshared_a_ps", "unshared_b_ps"):
            r[f] = r[f] * S
        rows.append(r)
    d["corners"][k]["all"] = rows
json.dump(dict(corners={k: d["corners"][k] for k in keys}), open(a.pre + "_xing_lpo.json", "w"))
rows = CAP.load_rows(a.pre + "_xing_lpo.json", ",".join(keys))
summ, out, regs = CAP.plan([dict(r) for r in rows], pad=a.pad)
mc = CAP.mc_check(CAP.load_rows(a.pre + "_xing_lpo.json", ",".join(keys)) and [dict(r, lo=r["d_ps"]-r["p_dn_ps"], hi=r["d_ps"]+r["p_up_ps"]) for r in rows], out, regs, chips=a.mc) if a.mc else None
json.dump(dict(summary=summ, crossings=out, regions=regs, mc=mc, scale=dict(TT=a.stt, FF=a.sff)), open(a.pre + "_ca.json", "w"), indent=0)
s = {k: summ[k] for k in ("regions_reached", "tree_root", "tree_edges", "tree_edges_clean", "crossings", "depth4", "depth8", "fail",
                          "max_path_ambiguous_cycles", "worst_margin_lo_ps", "worst_margin_lo_port", "worst_margin_hi_ps",
                          "worst_margin_hi_port", "below_100ps", "lat_total_vs_old3", "lat_hist")}
s["tree_edges_ambiguous"] = len(summ["tree_edges_ambiguous"]); s["mc"] = mc; s["scale"] = [a.stt, a.sff]
json.dump(s, open(a.pre + "_ca_summary.json", "w"), indent=1)
print(json.dumps(s))
