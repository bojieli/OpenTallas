"""LOCALITY-SCORE-2 calibration: feed the MEASURED LAND-HEAD-3 sfb branches (unshared a/b, dist) into locality.margins
(synthetic tree, stages = unshared/mu) and compare p_up/p_dn and the count-aligned margin with landed_phase_ocv on the
real routed tree."""
import json, sys
sys.path.insert(0, "tools/die_plan")  # run from the repo root; arg = git show ec4f9b4ac2:results/land_head_3_1027/routed_sfb/landed_ocv.json
import locality as LO, clk_aocv as CA
J = json.load(open(sys.argv[1]))
T = CA.load(LO.TABLE)
out = {}
for corner, key in (("TT", "TT_droop-regions_corelat250"), ("FF", "FF_droop-regions_corelat202.5")):
    rows = J["corners"][key]["all"]
    out[corner] = rows
TT, FF = out["TT"], out["FF"]
ffmap = {r["port"]: r for r in FF}
br = [dict(ua=r["unshared_a_ps"], ub=r["unshared_b_ps"], div=0.0, pts=[(0, 0), (r["dist_um"], 0)]) for r in TT]
M = LO.margins(br, T, 833.0)
dif_tt, dif_ff, ca_m, ca_meas, ca_mf, ca_measf = [], [], [], [], [], []
for r, m in zip(TT, M):
    f = ffmap[r["port"]]
    pm, pmeas = m["p_tt"], max(r["p_up_ps"], r["p_dn_ps"])
    dif_tt.append(pm - pmeas)
    ca_m.append(m["ca_tt"]); ca_meas.append(416.5 - pmeas)
    pmf = max(f["p_up_ps"], f["p_dn_ps"])
    dif_ff.append(m["p_ff"] - pmf)
    ca_mf.append(m["ca_ff"]); ca_measf.append(416.5 - pmf)
import statistics as st
print(json.dumps(dict(crossings=len(TT),
    p_model_minus_measured_TT=dict(mean=round(st.mean(dif_tt), 1), min=round(min(dif_tt), 1), max=round(max(dif_tt), 1)),
    p_model_minus_measured_FF=dict(mean=round(st.mean(dif_ff), 1), min=round(min(dif_ff), 1), max=round(max(dif_ff), 1)),
    ca_worst_model=[min(ca_m), min(ca_mf)], ca_worst_measured=[round(min(ca_meas), 1), round(min(ca_measf), 1)],
    max_unshared_measured_TT=max(max(r["unshared_a_ps"], r["unshared_b_ps"]) for r in TT)), indent=1))
