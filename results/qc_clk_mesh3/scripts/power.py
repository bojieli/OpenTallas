import json, sys, math
sys.path.insert(0, "/w/die_plan")
import argparse
import qc_clk_mesh3 as M
ap = argparse.ArgumentParser(); M.add_common(ap); ap.add_argument("--out"); a = ap.parse_args()
st = M.Stage(a.stage); B = M.build(a, st)
rec = B["rec"]; xs, ys = [M.r3(x) for x in rec["xs"]], [M.r3(y) for y in rec["ys"]]
drv = []
for ct in B["ctrees"]:
    drv += [(M.r3(n["xy"][0]), M.r3(n["xy"][1])) for n in ct["nodes"] if not n["kids"]]
NF = M.mesh([(y, xs[0], xs[-1]) for y in ys], [(x, ys[0], ys[-1]) for x in xs], sorted(set(drv)), [], M.RC3[a.fine_w], (M.RC3[a.stub_w], a.stub_um))
cf = sum(NF["C"].values()) / 1e3
cv = M.voronoi_c(NF); fm = M.size(cv, a.fine_m, a.sizing)
ew = lambda nodes: sum(n["leg"] for n in nodes if n.get("parent"))
nst = lambda nodes: sum(n["nseg"] for n in nodes if n.get("parent"))
ct = ew(B["top_nodes"]) * M.RC3[a.top_w]["M8"][1] / 1e3 + nst(B["top_nodes"]) * a.top_m * M.BUF_CIN_FF / 1e3
cc = ew(B["cnodes"]) * M.RC3[a.col_w]["M8"][1] / 1e3 + nst(B["cnodes"]) * a.col_m * M.BUF_CIN_FF / 1e3 + float(fm.sum()) * M.BUF_CIN_FF / 1e3
# buffer internal (short-circuit + internal nodes): BUFx24 ~ 2x its input cap equivalent, stated assumption
nbuf = nst(B["top_nodes"]) * a.top_m + nst(B["cnodes"]) * a.col_m + float(fm.sum())
cint = nbuf * 24 * 0.7 / 1e3      # ~0.7 fF per drive unit internal, UNCHECKED assumption
tot = cf + ct + cc + cint
P = {c: tot * 1e-9 * M.VDD[c] ** 2 * M.F_CLK for c in ("TT", "FF")}
out = dict(fine_mesh_nF=round(cf, 3), top_tree_nF=round(ct, 3), col_tree_and_driver_in_nF=round(cc, 3), buffer_internal_nF_assumed=round(cint, 3),
           total_nF=round(tot, 3), P_W={c: round(v, 3) for c, v in P.items()}, buffers_BUFx24_equiv=round(nbuf, 1),
           fine_drivers=[[q[0], q[1], round(float(cv[k]), 2), float(fm[k])] for k, q in enumerate(sorted(set(drv)))])
json.dump(out, open(a.out, "w"))
print(json.dumps({k: v for k, v in out.items() if k != "fine_drivers"}))
