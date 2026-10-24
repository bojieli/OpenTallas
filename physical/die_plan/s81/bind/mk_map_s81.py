#!/usr/bin/env python3
"""BINDER4-S81 10-23: as-built leaf -> S81 plan v4.6 partition map for tools/die_plan/bind.py (asbuilt.map_file).

Sources: the plan's instance_map.json (frames fW*_p* -> as-built f_*, inst_part svc/irg) and slice partitions
(C / L0..L4 / LP; x stations hold no as-built leaf).  Slice regions follow the landed parent's clock regions:
u_lf<k> (region L<k>) -> s_<id>_L<k>; mu72 slices: lep core u_lep, coll lanes u_ln*/u_lnl*, MU land u_land (+ their reset forests) -> LP,
the rest of the shell and u_sl.* -> C; plain slices (u_lp / u_slice / u_sl) -> C.  Usage: mk_map_s81.py instance_map.json OUT.json"""
import json
import sys

im = json.load(open(sys.argv[1]))
parts = {}
for pf, f in im["frames"].items():
    for r in range(3):
        parts[f"u_{f}.u_r{r}"] = f"{pf}_b{r}"
    parts[f"u_{f}"] = f"{pf}_b0"                       # wrapper glue (none expected)
for k, v in im["inst_part"].items():
    parts[k] = v
for k in range(16):
    parts[f"rinv_rsv_{k:02d}"] = im["inst_part"][f"u_rsv_{k:02d}"]   # reset inverter of the svc's active-high reset
for k, v in dict(u_bk_col="bk_col", u_gunit="gunit", u_bk_sel="bk_sel", u_eng="eng", u_iqf="iqf", u_seqhost="seqhost",
                 u_phy_hbm="phy_hbm").items():
    parts[k] = v
for lk in ["WS0", "WS1", "WN0", "WN1", "WN2", "WN3", "ES0", "ES1", "EN0", "EN1"]:
    parts[f"u_lk_{lk}"] = f"lk_{lk}"
parts["ld_pv_E"] = "s_4S_C"                            # pv landing clocked by ck_sl_s_4S_C
parts["ld_pv_W"] = "s_3S_C"                            # clocked by ck_b_s_3S
for s, sp in im["slice_part"].items():
    sid = s[4:]
    mu = sp.get("LP") is not None
    if mu:
        parts[s] = sp["C"]                             # shell glue, hbc host stage, MU-land ML flops, rx/tx reset roots
        for k in ["u_lep", "u_land", "u_lpr_K", "u_lpr_ML"] + [f"u_ln{j}" for j in range(4)] + [f"u_lnl{j}" for j in range(4)] \
                + [f"u_lpr_N{j}" for j in range(4)]:
            parts[f"{s}.{k}"] = sp["LP"]                # lep core K + coll lanes + MU land (gen_plan_v4 LP_CELLS)
        for k in range(5):
            parts[f"{s}.u_sl.u_lf{k}"] = f"s_{sid}_L{k}"
    else:
        parts[s] = sp["C"]
        for k in range(5):
            parts[f"{s}.u_lp.u_lf{k}"] = f"s_{sid}_L{k}"
            parts[f"{s}.u_slice.lf[{k}].u_lf"] = f"s_{sid}_L{k}"
            parts[f"{s}.u_sl.lf[{k}].u_lf"] = f"s_{sid}_L{k}"
json.dump(dict(note=__doc__.splitlines()[0], parts=parts, rules=[]), open(sys.argv[2], "w"), indent=0)
print(len(parts))
