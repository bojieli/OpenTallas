#!/usr/bin/env python3
"""HBM-CORE-LAT-R3 12.8c designed fixed trunk at the core clock entry (plan-only NLDM, no measured input).
Chain of N identical BUF stages (dont_touch, pushdown cells at the entry island) ahead of the CTS-open local tree.
Stage load = next stage input cap + 2 fF local wire; last stage drives the local tree root (BUFx8 class input + 2 fF).
Prints per-chain TT/FF delay and slew; the chosen chain meets need_TT = 250 - tree_TT (plan model) best."""
import sys, json
sys.path.insert(0, sys.argv[1])
from core_infra_htree import lib_cells, interp
cells = ["BUFx4_ASAP7_75t_R", "BUFx6f_ASAP7_75t_R", "BUFx8_ASAP7_75t_R", "BUFx10_ASAP7_75t_R"]
L = {c: lib_cells(f"lib/asap7sc7p5t_INVBUF_RVT_{c}_nldm_220122.lib", cells + ["BUFx8_ASAP7_75t_R"]) for c in ("TT", "FF")}
def chain(cell, n, corner, s0=20.0, wire=2.0):
    lc = L[corner]; s = s0; d = 0.0
    for i in range(n):
        load = (lc[cell]["cin"] if i < n - 1 else lc["BUFx8_ASAP7_75t_R"]["cin"]) + wire
        dr, df = interp(lc[cell]["rise"], s, load), interp(lc[cell]["fall"], s, load)
        sr, sf = interp(lc[cell]["trise"], s, load), interp(lc[cell]["tfall"], s, load)
        d += max(dr, df); s = max(sr, sf)
    return d, s
need = dict(argmax=(250 - 102.2, 202.5 - 81.8), collar=(250 - 94.9, 202.5 - 75.9))
res = {}
for c in cells:
    for n in range(3, 10):
        tt, stt = chain(c, n, "TT"); ff, sff = chain(c, n, "FF")
        res[f"{c}x{n}"] = dict(cell=c, n=n, tt=round(tt, 2), ff=round(ff, 2), slew_tt=round(stt, 2))
pick = {}
for k, (ntt, nff) in need.items():
    best = min(res.values(), key=lambda r: abs(r["tt"] - ntt) + abs(r["ff"] - nff))
    pick[k] = dict(need_tt=round(ntt, 1), need_ff=round(nff, 1), **best)
print(json.dumps(dict(chains=res, pick=pick), indent=1))
