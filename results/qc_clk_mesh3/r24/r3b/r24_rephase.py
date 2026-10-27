#!/usr/bin/env python3
"""INFRA-FIRST-QC-R24: adopt the QC-CORES-2 A0-CLK-R3b strap re-phase (f217587b2) in the d51 mesh lattice and run the
whole-die mesh RC MC (qc_clk_mesh2 netlist/solve, linear RC + Thevenin drivers) with the 768 x 22 = 16,896 A0 island drop
loads.  Re-phase: every R22/R23 M9 strap whose x lies over an A0 core column [x0, x0+457.92] and every M8 strap whose y lies
over an A0 core row [y0, y0+1157.76] is replaced by the A0-commensurate drop straps x0+U / y0+V (MX: y0+H-V); straps outside
the A0 field (channels, inter-row bands, centre band) and every driver column are kept.  W-column extension: the drop straps
of the W column (x0 1650.24) lie W of the first R23 strap (2177.28) and extend the mesh to x 1762.56; drop rows outside the
R23 M8 span extend it in y.  Drop load = one island driver input (BUF_CIN_FF) at the M9 x M8 crossing (die stub 0).
usage: r24_rephase.py R2 R3B_JSON QCDIR OUTDIR [--corner TT] [--samples N] [--mode rephase|base]"""
import argparse, json, sys
from pathlib import Path
ap = argparse.ArgumentParser()
ap.add_argument("r2"); ap.add_argument("r3b"); ap.add_argument("qc"); ap.add_argument("out")
ap.add_argument("--thev", required=True); ap.add_argument("--corner", default="TT"); ap.add_argument("--samples", type=int, default=0)
ap.add_argument("--mode", default="rephase", choices=["rephase", "base", "add"])
ap.add_argument("--sigma", default='{"vt_mV": 10.0, "wire_rel": 0.05, "tree_ps_per_stage": 2.0}')
a = ap.parse_args()
sys.path.insert(0, a.qc)
import qc_clk_mesh2 as Q
CW, CH = 457.92, 1157.76
rec = json.load(open(a.r2)); R3 = json.load(open(a.r3b))
L = R3["lattices"]["R23_d51_candidate"]; U, V = R3["type_lattice"]["m9_u"], R3["type_lattice"]["m8_v"]
isl = R3["islands"]
inst = L["per_instance"]
r3 = Q.r3
cols0 = sorted({q["x0"] for q in inst}); rows0 = sorted({q["y0"] for q in inst})
over_x = lambda x: any(c - 1e-6 <= x <= c + CW + 1e-6 for c in cols0)
over_y = lambda y: any(r - 1e-6 <= y <= r + CH + 1e-6 for r in rows0)
reqx = sorted({r3(q["x0"] + u) for q in inst for u in U})
reqy = sorted({r3(q["y0"] + (CH - v if q["mx"] else v)) for q in inst for v in V})
drops = []
for q in inst:
    for n, t in isl.items():
        u, v = t["drop_core_frame"]
        drops.append(dict(part=f"drop:{q['n']}:{n}", entry=None, tap=[r3(q["x0"] + u), r3(q["y0"] + (CH - v if q["mx"] else v))], stub_um=0.0))
info = dict(mode=a.mode, r2_xs=len(rec["xs"]), r2_ys=len(rec["ys"]), drops=len(drops))
if a.mode in ("rephase", "add"):
    dcol = {r3(x) for x in rec["driver_columns"]}
    kx = [r3(x) for x in rec["xs"] if a.mode == "add" or not over_x(x) or r3(x) in dcol]
    ky = [r3(y) for y in rec["ys"] if a.mode == "add" or not over_y(y)]
    xs = sorted(set(kx) | set(reqx)); ys = sorted(set(ky) | set(reqy))
    info.update(kept_m9=len(kx), kept_m8=len(ky), drop_m9=len(reqx), drop_m8=len(reqy), m9=len(xs), m8=len(ys),
                removed_m9=len(rec["xs"]) - len(kx), removed_m8=len(rec["ys"]) - len(ky),
                driver_cols_over_a0=sorted(x for x in dcol if over_x(x)),
                x_span=[xs[0], xs[-1]], y_span=[ys[0], ys[-1]], r2_x_span=[rec["xs"][0], rec["xs"][-1]], r2_y_span=[rec["ys"][0], rec["ys"][-1]])
    rec = dict(rec, xs=xs, ys=ys, taps=list(rec["taps"]) + drops)
    sx, sy = set(xs), set(ys)
    info["drops_on_crossing"] = sum(1 for d in drops if d["tap"][0] in sx and d["tap"][1] in sy)
    spanx = (xs[-1] - xs[0]) / 1000; spany = (ys[-1] - ys[0]) / 1000
    info["mesh_m"] = dict(m9=round(len(xs) * spany, 2), m8=round(len(ys) * spanx, 2),
                          )
Path(a.out).mkdir(parents=True, exist_ok=True)
json.dump(dict(info, xs=rec["xs"], ys=rec["ys"]), open(Path(a.out) / f"lattice_{a.mode}.json", "w"), indent=0)
print(json.dumps(info), flush=True)
sig = json.loads(a.sigma); thev = json.load(open(a.thev))
out = dict(info=info, corner=a.corner, sigma=sig, samples=[])
for s in range(a.samples + 1):
    N = Q.netlist(rec, a.corner, None, 0.0, sigma=sig, seed=s)
    ctot = sum(N["C"].values())
    res, t0 = Q.solve_netlist(N, a.corner, thev)
    xc = [v for k, v in res.items() if k[0] == "x"]
    tp = {k[1]: v for k, v in res.items() if k[0] == "t"}
    pt = [v for k, v in tp.items() if not k.startswith("drop:")]
    dp = [v for k, v in tp.items() if k.startswith("drop:")]
    row = dict(sample=s, nodes=N["nodes"], drivers=len(N["drv"]), taps_attached=len(N["taps"]), c_total_pf=round(ctot / 1000, 1),
               crossing_spread_ps=r3(max(xc) - min(xc)), part_tap_skew_ps=r3(max(pt) - min(pt)) if pt else None,
               drop_n=len(dp), drop_skew_ps=r3(max(dp) - min(dp)) if dp else None,
               all_tap_skew_ps=r3(max(tp.values()) - min(tp.values())), t_first=r3(min(tp.values())), t_last=r3(max(tp.values())))
    import collections
    bc = collections.defaultdict(list)
    for k, v in tp.items():
        if k.startswith("drop:"):
            bc[k.split(":")[1]].append(v)
    if bc:
        sp = sorted(max(v) - min(v) for v in bc.values())
        row["in_core_drop_spread_ps"] = dict(n=len(sp), median=r3(sp[len(sp) // 2]), p90=r3(sp[int(len(sp) * 0.9)]), max=r3(sp[-1]))
    if s == 0:
        row["tap_arr_ps"] = {k: r3(v) for k, v in tp.items()}
    out["samples"].append(row)
    print(json.dumps({k: v for k, v in row.items() if k != "tap_arr_ps"}), flush=True)
    json.dump(out, open(Path(a.out) / f"mc_{a.mode}_{a.corner}.json", "w"))
