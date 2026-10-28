#!/usr/bin/env python3
"""CA-OCV-1 independent hand trace of ONE CA crossing (no die_sta_related / clk_aocv import): raw tap JSON + table JSON.
usage: hand_trace.py PROOF PLAN BIND TABLE PORT CORNER LAT_PS"""
import json, math, sys
from pathlib import Path
proof, plan_p, bind_p, table_p, port, C, lat = sys.argv[1:8]
lat = float(lat)
S = {"TT": 1.0485, "FF": 1.0552}[C]
T = 833.333
t = json.loads((Path(proof) / f"tap_arrivals_{C}.json").read_text())
taps = {r["port"]: r for r in t["taps"]}
plan, bind = json.loads(Path(plan_p).read_text()), json.loads(Path(bind_p).read_text())
tab = json.loads(Path(table_p).read_text()); tab = tab.get("clock_aocv", tab)
dreg = json.loads((Path(proof) / "droop_regions.json").read_text())
b = bind["ports"][port]
reg = {p: v["region"] for p, v in bind["parts"].items() if isinstance(v, dict) and v.get("region")}
src, dst = b["src"], b["dst"]
# partition pairs connected by a plan port whose regions are (src, dst) and that sit in different cppr regions
conn = {(p["src"]["part"], p["dst"]["part"]) for p in plan["ports"] if p["src"]["part"] != p["dst"]["part"]}
byp = {}
for k, r in taps.items():
    byp.setdefault(r["part"], []).append(k)
def lca(x, y):
    n = 0
    while n < min(len(x), len(y)) and x[n] == y[n]:
        n += 1
    return x[:max(1, n)]
A, Bc = tab["classes"]["A"][C], tab["classes"]["B"][C]
nB = max(1, round(lat / Bc["mu_stage_ps"]))
def rfrac(nA):
    var = (A["mu_cell_ps"] * A["s_cell"]) ** 2 * nA
    vb = nB + 2 * sum((nB - l) * r for l, r in enumerate(Bc["rho"], 1) if l < nB)
    var += (Bc["mu_cell_ps"] * Bc["s_cell"]) ** 2 * vb
    return tab["k_sigma"] * math.sqrt(var) / (nA * A["mu_cell_ps"] + nB * Bc["mu_cell_ps"])
def side(arr, nA):
    return (A["cell_share"] * arr + Bc["cell_share"] * lat, (1 - A["cell_share"]) * arr + (1 - Bc["cell_share"]) * lat, rfrac(nA))
best = None
for (ps, pd) in conn:
    if reg.get(ps) != src or reg.get(pd) != dst:
        continue
    for a in byp.get(ps, []):
        for c in byp.get(pd, []):
            ta, tc = taps[a], taps[c]
            if ta["cppr_node"] == tc["cppr_node"]:
                continue
            node = lca(ta["tree_path"], tc["tree_path"])
            la, ea, lc, ec = (S * ta["late_ps"], S * ta["early_ps"], S * tc["late_ps"], S * tc["early_ps"])
            nl, ne = S * t["node_late_ps"][node], S * t["node_early_ps"][node]
            rngn = node
            while rngn not in t["cppr_node_range_ps"] and len(rngn) > 1:
                rngn = rngn[:-1]
            cr = min(max(0, S * t["cppr_node_range_ps"].get(rngn, 0)), la - ea, lc - ec)
            lo0 = ec - la + cr
            # setup pessimism: launch a late branch, capture c early branch
            nx = t["node_xy_um"][node]
            pts = [ta["xy_um"], tc["xy_um"]] + ([nx] if nx else [])
            dist = math.hypot(max(p[0] for p in pts) - min(p[0] for p in pts), max(p[1] for p in pts) - min(p[1] for p in pts))
            g = tab["systematic"]["g_per_mm"] * dist / 1000 / 2
            stA = ta["stages_from_root"] - t["node_stages"][node]
            stC = tc["stages_from_root"] - t["node_stages"][node]
            cl, nl_, rl = side(la - nl, stA)
            ce, ne_, re_ = side(ec - ne, stC)
            same = dreg.get(a) is not None and dreg.get(a) == dreg.get(c)
            droop = 0 if same else tab["droop"]["one_sided_late_frac"]
            ocv = cl * (rl + g + droop) + ce * (re_ + g) + nl_ * (tab["net_flat"]["late"] - 1) + ne_ * (1 - tab["net_flat"]["early"])
            lo = lo0 - ocv
            if best is None or lo < best[0]:
                best = (lo, lo0, ocv, a, c, node, la, ea, lc, ec, cr, dist, stA, stC, droop, la - nl, ec - ne)
lo, lo0, ocv, a, c, node, la, ea, lc, ec, cr, dist, stA, stC, droop, bra, brc = best
L_lo = b["L_lo_ps"] + (lo - b["d_lo_ps"])
L_lo0 = b["L_lo_ps"] + (lo0 - b["d_lo_ps"])
print(json.dumps(dict(port=port, corner=C, region_pair=f"{src}->{dst}", K=b["K"], depth=b["depth"], launch=a, capture=c, lca=node,
                      launch_late=round(la, 1), launch_early=round(ea, 1), capture_late=round(lc, 1), capture_early=round(ec, 1),
                      cppr_credit=round(cr, 2), branch_launch_late=round(bra, 1), branch_capture_early=round(brc, 1),
                      stages=[stA, stC], bbox_mm=round(dist / 1000, 3), droop_frac=droop,
                      d_lo_sta=round(lo0, 1), ocv_setup=round(ocv, 1), d_lo_with_ocv=round(lo, 1),
                      bind_d_lo=b["d_lo_ps"], margin_lo_no_ocv=round(L_lo0 - T / 2, 1), margin_lo_with_ocv=round(L_lo - T / 2, 1)), indent=1))
