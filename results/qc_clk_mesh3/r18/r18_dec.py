import json, sys, statistics as S
R = sys.argv[1]
for N in ("base", "m_t0", "m_g0", "m_tr", "f64", "f64_t0"):
    out = [N]
    for c in ("TT", "FF"):
        s = json.load(open(f"{R}/{N}/die_{c}.json"))["summary"]
        pu = json.load(open(f"{R}/{N}/sta_in/pair_unc.json"))
        mv = sorted(r[c]["mesh_mc_var_ps"] for r in pu["rows"])
        st = json.load(open(f"{R}/{N}/sta/die_sta_related.json"))["corners"][c]["classes"]["seam"]
        out.append(f"{c}: nom {s['nominal_tap_skew_ps']:.2f} MCworst {s['mc_worst_tap_skew_ps']:.1f} ins {s['insertion_ps']['min']:.0f}-{s['insertion_ps']['max']:.0f} "
                   f"pairMCvar med {S.median(mv):.1f} max {mv[-1]:.1f} hold {st['worst_hold_slack_ps']:.2f} setup {st['worst_setup_slack_ps']:.2f}")
    print(" | ".join(out))
