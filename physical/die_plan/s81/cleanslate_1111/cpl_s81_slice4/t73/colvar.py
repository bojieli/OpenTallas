#!/usr/bin/env python3
"""CPL-S81-SLICE-4 scoring-only variants for col types (NOT a delta): edit one type in a copy of the plan, keep only
listed types (route_supply --types reads them).  usage: colvar.py BASE OUT VARIANT"""
import json, sys, copy
base, outp, var = sys.argv[1:4]
P = json.load(open(base)); T = P["partition_types"]
def st(t, conn): return next(s for s in t["internal_stations"] if s["conn"] == conn)
def ft(t, n): return next(f for f in t["ft_slots"] if f["name"] == n)
def mv_ft(f, ys=None, xs=None):
    for k in range(1, len(f["regs_um"])):
        r = f["regs_um"][k]; dx = (xs[k - 1] - r[0]) if xs else 0; dy = (ys[k - 1] - r[1]) if ys else 0
        f["regs_um"][k] = [r[0] + dx, r[1] + dy]
        f["bit_sites_um"][k - 1] = [[p[0] + dx, p[1] + dy] for p in f["bit_sites_um"][k - 1]]
for tn in ("col_h10_r0_p1__t1__cl574cc59d", "col_h10_r0_p1__t1__cl911743eb"):
    t = T[tn]
    if "fio" in var:   # frame_int_o0 relay off the E face strip: vertical leg in the 1296-1339 node street
        s = st(t, "bus:frame_int_o0"); s["regs_um"][-1] = [1317.6, 931.222]; s["regs_um"][-2] = [1317.6, 1226.88]
    if "ft0" in var:   # ft0 interior sites: y of the clear row gap
        f = ft(t, "ft0"); y = float(var.split("ft0=")[1].split(",")[0]); mv_ft(f, ys=[y] * (len(f["regs_um"]) - 1))
    bd = t["clock"]["landing_contract"]["bands"]
    if "b1" in var and "x_i0" in bd: bd["x_i0"]["rect_um"] = [1313.28, 739.584, 1425.6, 979.548]
    if "n9" in var:
        next(h for h in t["hard_cores"] if h["inst"] == "u_r0.u_n9")["origin_um"] = [1252.8, 1002.24]
        if "ft0_i" in bd: bd["ft0_i"]["rect_um"] = [1339.2, 969.636, 1425.6, 1209.6]
json.dump(P, open(outp, "w"), separators=(",", ":"))
