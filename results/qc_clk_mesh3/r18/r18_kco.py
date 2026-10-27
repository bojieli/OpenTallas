import json, sys, collections
R = sys.argv[1]
for N in ("base", "f64", "f64_t0"):
    for v in ("sta", "sta_cv"):
        d = json.load(open(f"{R}/{N}/{v}/die_sta_related.json"))
        s = d["corners"]["FF"]["classes"]["seam"]
        k, o = s["kit_contract_hold"], s.get("kit_contract_hold_ocv")
        res = o["residual_ps"] if o else []
        bins = collections.Counter(min(4, int(r[0] // 20)) for r in res)
        print(f"{N:7s} {v:6s} kit {k['worst_hold_bound_ps']:7.2f} neg {k['neg_pairs']:3d} {k['worst']['where']} | +OCV {o['worst_hold_bound_ps']:8.2f} "
              f"neg {o['neg_pairs']:4d} pctl {o['damage_plus_ocv_pctl_ps']} worst {o['worst']['where']} resid bins(20ps) {dict(sorted(bins.items()))}")
