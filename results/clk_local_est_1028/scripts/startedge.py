#!/usr/bin/env python3
"""local form start edges: a dedicated start port per feed edge at the clock fork (the feed tap t on the parent spine):
launch flop at t on the parent clock (0 unshared below the fork), capture sync flop at the child's region root entry
(unshared = the forwarded spine t -> child centre).  OCV with clk_aocv g021 branch_pessimism (class A stages, nets
+-3 %, 0.21 %/mm, one-sided droop: different regions), x spice; width = setup + hold terms + 2 x 10 ps pin-cap range.
Also the same with the sync flop at the farthest leaf of the child (worst placement).  usage: startedge.py REPO LOCJSON V"""
import json, sys, math
repo, lj, v = sys.argv[1], sys.argv[2], float(sys.argv[3])
sys.path.insert(0, f"{repo}/tools/die_plan")
import clk_aocv as CA
T = CA.load(f"{repo}/tools/die_plan/clk_aocv_table_g021.json")
L = json.load(open(lj)); G = {g["region"]: g for g in L["regions"]}
F = L["feed"]; tap = F["tap"]
# region centres are not in the summary rows: reconstruct from feed taps is not possible -> use loc rows xy? use the regions file
ap = 833.333 / 8
def ocv(U, dist_um, corner, spice):
    A = T["classes"]["A"][corner]; fc = A["cell_share"]; U = U * spice
    br = dict(cell_ps=fc * U, net_ps=(1 - fc) * U, stages={"A": max(1, round(U / A["mu_stage_ps"]))})
    z = dict(cell_ps=0.0, net_ps=0.0, stages={"A": 0})
    s = CA.branch_pessimism(T, corner, z, br, dist_um, False, "setup")
    h = CA.branch_pessimism(T, corner, z, br, dist_um, False, "hold")
    return s, h
ff = T["classes"]["A"]["FF"]["mu_stage_ps"] / T["classes"]["A"]["TT"]["mu_stage_ps"]
res = []
for k, t in tap.items():
    p, c = k.split("->"); g = G[c]
    # child centre from bbox not stored; use w/h and the ins model: spine t->centre <= (w+h)/2 (worst) ; leaf worst = +(w+h)/2
    d_root = (g["w_mm"] + g["h_mm"]) / 2 * 1000  # conservative: tap at the child's far corner
    for where, um in (("root", d_root), ("leaf", 2 * d_root)):
        U = v * um / 1000
        w = 0
        for corner, sc, sp in (("TT", 1.0, 1.0485), ("FF", ff, 1.0552)):
            s, h = ocv(U * sc, um, corner, sp)
            w = max(w, s + h + 20)
        res.append((where, U, w, k))
for where in ("root", "leaf"):
    r = [x for x in res if x[0] == where]; ws = sorted(x[2] for x in r); us = sorted(x[1] for x in r)
    print(f"start edge sync at child {where}: edges {len(r)} U ns med {us[len(us)//2]/1e3:.2f} max {us[-1]/1e3:.2f}; width ps med {ws[len(ws)//2]:.0f} max {ws[-1]:.0f}; clean-guaranteed (<= {833.333/2-2*ap:.0f}) {sum(w <= 833.333/2-2*ap for w in ws)}/{len(ws)}")
