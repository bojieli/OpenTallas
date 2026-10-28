# HBM-CORE-LAT-2 (2026-10-28): per HBM hard-core module, the clock insertion TT/FF (mean/min/max over sinks) from
# the best available source, the early_ps table for plan core taps (gen_phys core_tap_rows / core_latency_files:
# tap insertion_ps = TT mean, insertion_ff_ps = FF mean; early = max(0, ins - common latency 250 TT / 202.5 FF)),
# and the boundary FF hold estimate with early taps (same model basis as HBM-RISK-2 R3, UNCHECKED model).
#   build.py gather.json probes.json OUT_PREFIX
import json, sys, statistics
G = json.load(open(sys.argv[1])); PR = json.load(open(sys.argv[2])); OUT = sys.argv[3]
TT0, FF0 = 250.0, 202.5
M0 = 25.0          # R3 basis: parent zero-logic reg -> core pin reg, clk->q + short wire - hold (UNCHECKED)
OCV = 0.05         # R3 basis: unshared core-internal tree OCV (AOCV ~5 %, UNCHECKED)
U_HOLD = 25.0      # METHODOLOGY 6.1 hold uncertainty
SPREAD_LIM = 150.0
# FF/TT ratio from the routed views (insertion.json) -- used only where a source has TT only
rat = []
for r in G:
    ij = r.get("insertion_json")
    if ij and ij.get("tt", {}).get("all") and ij.get("ff", {}).get("all"):
        rat.append(ij["ff"]["all"]["mean"] / ij["tt"]["all"]["mean"])
FFR = round(statistics.mean(rat), 4)
rows = []
for r in G:
    m = r["module"]; src = None; pins = None
    ij = r.get("insertion_json"); pr = PR.get(m)
    if ij and ij.get("tt"):
        b = "boundary" if ij["tt"].get("boundary") else "all"
        t, f = ij["tt"][b], ij["ff"][b]
        src = dict(source=f"real routed view {ij['path']} ({ij['parasitics']}, {ij['db']}, {b} regs n={t['n']})",
                   label="CHECKED (measured routed SPEF view, plan-selected lib; NUMBER-CHECK not independent)",
                   tt=dict(mean=t["mean"], min=t["min"], max=t["max"]), ff=dict(mean=f["mean"], min=f["min"], max=f["max"]))
        if ij.get("clock_measurements") and len(ij["clock_measurements"]) > 1:
            pins = "MULTI-CLOCK view: %d clock pins (%s); plan taps '*' = one insertion for all pins -> per-pin taps needed" % (
                len(ij["clock_measurements"]), ",".join(ij["clock_measurements"][:6]))
    elif pr and pr.get("tt"):
        src = dict(source=pr["source"], label=pr["label"], tt=pr["tt"], ff=pr["ff"])
        pins = pr.get("multi")
    elif r.get("b2l_exact"):
        x = r["b2l_exact"][0]; same = [round(a, 1) for a in x["outline"]] == [round(a, 1) for a in r["outline"]]
        po = x["ports"]; mn = min(v["min_ps"] for v in po.values() if v["sinks"] > 1)
        src = dict(source=f"b2l natural CTS (TritonCTS it0, placement RC) {x['view']} outline {x['outline']}" + ("" if same else f" != plan {r['outline']} (OLD OUTLINE)"),
                   label="UNCHECKED (old kit, placement RC" + ("" if same else ", outline changed") + f"; FF = TT x {FFR} routed-view ratio)",
                   tt=dict(mean=x["mean"], min=mn, max=x["max"]), ff=dict(mean=round(x["mean"] * FFR, 1), min=round(mn * FFR, 1), max=round(x["max"] * FFR, 1)))
        if len([p for p, v in po.items() if v["sinks"] > 1]) > 1:
            pins = "MULTI-CLOCK old kit: " + ", ".join(f"{p} {v['mean_ps']}" for p, v in po.items() if v["sinks"] > 1)
    elif r.get("b2l_proxy"):
        xs = r["b2l_proxy"]; mean = round(statistics.mean(x["mean"] for x in xs), 1)
        mn = min(x["minp"] for x in xs); mx = max(x["max"] for x in xs)
        src = dict(source=f"FAMILY PROXY: b2l natural CTS of {len(xs)} related old kits ({xs[0]['view'].split('@')[0]}, outline {xs[0]['outline']} vs plan {r['outline']})",
                   label=f"UNCHECKED (proxy of a related design; FF = TT x {FFR})",
                   tt=dict(mean=mean, min=mn, max=mx), ff=dict(mean=round(mean * FFR, 1), min=round(mn * FFR, 1), max=round(mx * FFR, 1)))
    else:
        tt = r["r4_formula_tt"]
        src = dict(source=f"r4 centre-entry model TT = 0.9429 x 0.8963 ps/um x Lmax {r['Lmax_um']} um (plan entry -> farthest corner)",
                   label="UNCHECKED model (no view, no kit CTS; spread unknown, 0 assumed)",
                   tt=dict(mean=tt, min=tt, max=tt), ff=dict(mean=r["r4_formula_ff"], min=r["r4_formula_ff"], max=r["r4_formula_ff"]))
    t, f = src["tt"], src["ff"]
    e_tt = round(max(0.0, t["mean"] - TT0), 1); e_ff = round(max(0.0, f["mean"] - FF0), 1)
    spread_tt = round(t["max"] - t["min"], 1); spread_ff = round(f["max"] - f["min"], 1)
    shallow_ff = round(max(0.0, FF0 - f["mean"]), 1)          # core earlier than common: early taps cannot fix
    # before (zero early, as planned now): core boundary capture late by max - 202.5
    hold_before = round(min(M0 - (f["max"] - FF0) - OCV * f["max"], M0 - (FF0 - f["min"]) - OCV * f["min"]), 1)
    resid = round(max(f["max"] - f["mean"] - shallow_ff, f["mean"] - f["min"] + shallow_ff), 1)   # worst boundary skew after early taps
    # with early taps at the FF mean: input side residual max-mean (+ shallow credit), output side mean-min (+ shallow debit)
    hin = M0 - (f["max"] - f["mean"] - shallow_ff) - OCV * f["max"]
    hout = M0 - (f["mean"] - f["min"] + shallow_ff) - OCV * f["min"]
    hold_after = round(min(hin, hout), 1)
    flags = []
    if spread_ff > SPREAD_LIM or spread_tt > SPREAD_LIM: flags.append(f"SPREAD>{SPREAD_LIM:g} (TT {spread_tt}): early taps cannot fix, in-core fix")
    if shallow_ff > 20: flags.append(f"SHALLOW (FF mean {f['mean']} < 202.5-20): early taps give 0; in-core fixed trunk 12.8c or late delivery")
    if pins: flags.append(pins)
    if "UNCHECKED model" in src["label"]: flags.append("NO DATA: model only")
    rows.append(dict(module=m, placements=r["placements"], types=r["types"], outline=r["outline"], source=src["source"],
                     label=src["label"], tt=t, ff=f, spread_tt=spread_tt, spread_ff=spread_ff,
                     insertion_ps=t["mean"], insertion_ff_ps=f["mean"], early_tt_ps=e_tt, early_ff_ps=e_ff,
                     hold_ff_before=hold_before, hold_in=round(hin, 1), hold_out=round(hout, 1), hold_ff_after=hold_after,
                     hold_ff_after_u25=round(hold_after - U_HOLD, 1), residual_skew_ff_ps=resid,
                     gate=("UNPROVEN (model, spread unknown)" if "UNCHECKED model" in src["label"] else ("PASS" if hold_after >= 0 else "FAIL")), flags=flags,
                     r3_basis=r.get("r4")))
json.dump(dict(schema="opentallas.hbm_core_lat_2.early_taps.v1", plan="C20h die-hbm-1027/c20h/die_plan.json sha 2e5644cf5f65",
               common_latency=dict(tt=TT0, ff=FF0), ff_tt_ratio_routed_views=FFR, n_ratio=len(rat),
               hold_model=dict(m0_ps=M0, ocv=OCV, u_hold_ps=U_HOLD, label="UNCHECKED model (HBM-RISK-2 R3 basis)"),
               tap_rule="each plan core tap of the module: insertion_ps = TT mean, insertion_ff_ps = FF mean, budget_owner = source "
                        "(not SIGNED -> gen_phys keeps the legacy core_latency path; signed_mean_core_taps only when SIGNED)",
               rows=rows), open(OUT + ".json", "w"), indent=1)
with open(OUT + ".tsv", "w") as fh:
    fh.write("module\tplacements\tinsertion_ps_tt_mean\ttt_min\ttt_max\tinsertion_ff_ps_mean\tff_min\tff_max\tearly_tt_ps\tearly_ff_ps\t"
             "spread_tt\tresidual_skew_ff\thold_ff_before\thold_ff_after\thold_after_u25\tgate\tlabel\tsource\tflags\n")
    for x in rows:
        fh.write("\t".join(str(v) for v in (x["module"], x["placements"], x["tt"]["mean"], x["tt"]["min"], x["tt"]["max"], x["ff"]["mean"],
                 x["ff"]["min"], x["ff"]["max"], x["early_tt_ps"], x["early_ff_ps"], x["spread_tt"], x["residual_skew_ff_ps"], x["hold_ff_before"], x["hold_ff_after"],
                 x["hold_ff_after_u25"], x["gate"], x["label"], x["source"], " | ".join(x["flags"]))) + "\n")
print("FF/TT ratio", FFR, "n", len(rat))
for x in sorted(rows, key=lambda x: x["hold_ff_after"]):
    print(f"{x['module'][:46]:46s} {x['placements']:4d} TT {x['tt']['mean']:7.1f} ({x['tt']['min']:.0f}-{x['tt']['max']:.0f}) FF {x['ff']['mean']:6.1f} "
          f"e {x['early_tt_ps']:6.1f}/{x['early_ff_ps']:6.1f} hold {x['hold_ff_before']:7.1f} -> {x['hold_ff_after']:6.1f} {x['gate'][:8]} res {x['residual_skew_ff_ps']} "
          f"{x['label'][:10]} {'; '.join(f[:40] for f in x['flags'])}")
