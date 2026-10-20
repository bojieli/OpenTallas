#!/usr/bin/env python3
"""SVC2: physical/ref_tile/dsdv_svc_rs_attw/spec.json (attw hardened child).  usage: mk_attw_spec.py WT STD_AREA_UM2 [PMEM] [HG_W HG_H]
SVC3 10-19: + the engine's 16 hard head groups (kit s81svc_attn_hgrp, ot_hdc_v41x_attn_hgrp_s81; tile_s built with
-DOT_ATTN_HGRP_HARD) as a 4 x 4 block of children on the 43.2 lattice, tile t = column, group g = row, centred
between the W (landing / p store) and E (staging) macro columns; STD_AREA = attw with the groups black-boxed."""
import json, math, sys
WT, A = sys.argv[1], float(sys.argv[2]); PMEM = int(sys.argv[3]) if len(sys.argv) > 3 else 1
G = 43.2
BW, BH = 172.8, 41.04           # ot_sram_1r1w_256x256_m2_r2c2
SW, SH = 51.408, 20.79          # ot_sram_1r1w_32x128_m1
HGW = float(sys.argv[4]) if len(sys.argv) > 4 else 388.8; HGH = float(sys.argv[5]) if len(sys.argv) > 5 else 388.8
CH = 2 * G                                    # child-child channel (>= 20 um, lattice multiple)
big = 16 + 12 + (4 if PMEM else 0); small = 12 + 5 + 4 + (17 if PMEM else 0)
macro_area = big * BW * BH + small * SW * SH
child_blk_w = 4 * HGW + 3 * CH; child_blk_h = 4 * HGH + 3 * CH
core = A / 0.50 + macro_area * 1.35 + (child_blk_w + 2 * G) * (child_blk_h + 2 * G)          # std cells at ~50 % + macros with halo / channel
side = math.sqrt(core)
W = math.ceil(side * 1.15 / G) * G
W = max(W, math.ceil((G + BW + G + SW + 2 * G + child_blk_w + 2 * G + BW + G) / G) * G)   # W cols | children | E col
H = math.ceil(core / W / G) * G
H = max(H, math.ceil((2 * 8 * BH + 3 * G) / G) * G, math.ceil((child_blk_h + 4 * G) / G) * G)
lat = lambda v: round(v / G) * G
ms = []
def big_stack(x, y, insts, orient="R0"):
    for i, n in enumerate(insts):
        ms.append({"view": "physical/asap7_memory_macros/ot_sram_1r1w_256x256_m2_r2c2", "inst": n,
                   "at": [round(x, 3), round(y + i * BH, 3)], "orient": orient if i % 2 == 0 else ("MX" if orient == "R0" else "R180")})
def small_stack(x, y, insts):
    for i, n in enumerate(insts):
        ms.append({"view": "physical/asap7_memory_macros/ot_sram_1r1w_32x128_m1", "inst": n,
                   "at": [round(x, 3), round(y + i * SH, 3)], "orient": "R0" if i % 2 == 0 else "MX"})
stage = [f"*u_stage{s}.g_macro.g_lane?{l}?.g_slice?{k}?.g_256.u_mem" for s in (0, 1) for l in range(4) for k in range(2)]
land = [f"*u_core.g_land?{c}?.g_b?{b}?.u_mem" for b in range(4) for c in range(3)]
pmem = [f"*u_core.g_pmem.g_bank?{b}?.g_half?{h}?.u_mem" for b in range(2) for h in range(2)] if PMEM else []
xe = lat(W - G - BW - 0.01) if lat(W - G - BW) + BW <= W - G + 1e-6 else lat(W - G - BW) - G
xe = math.floor((W - G - BW) / G) * G
top = lambda n, h: math.floor((H - G - n * h) / G) * G
big_stack(G, G, land)                         # W bottom: landing 12
if pmem: big_stack(G, top(4, BH), pmem)       # W top: p store 4
big_stack(xe, G, stage[:8]); big_stack(xe, top(8, BH), stage[8:])   # E: engine staging 2 x 8
wq = [f"*u_core.g_wqh?{c}?.g_p?{p}?.g_m.u_wqm.g_m?{k}?.u_m" for c in (0, 2) for p in (0, 1) for k in range(3)]
sw = [f"*u_core.u_swm.g_m?{k}?.u_m" for k in range(5)]
qm = [f"*u_core.u_qmm.g_m?{k}?.u_m" for k in range(4)]
pv = [f"*u_core.g_pvq.u_pvm.g_m?{k}?.u_m" for k in range(17)] if PMEM else []
xs = G + BW + G                               # small column right of the W big stacks
small_stack(xs, G, wq + sw)
small_stack(xs, top(4, SH), qm)
if pv: small_stack(math.floor((xe - G - SW) / G) * G, G, pv)
xl = G + BW + G + SW + G                      # W macro columns end
x0 = math.ceil((xl + G) / G) * G; y0 = math.ceil(((H - child_blk_h) / 2) / G) * G
ch = [{"view": "physical/ref_tile/s81svc_attn_hgrp/views/ot_hdc_v41x_attn_hgrp_s81",
       "inst": f"*u_eng.g_t?{t}?.g_ts.u_t.g_g?{g}?.u_g",
       "at": [round(x0 + t * (HGW + CH), 3), round(y0 + g * (HGH + CH), 3)]} for t in range(4) for g in range(4)]
assert x0 + child_blk_w <= xe - G + 1e-6, f"children overlap the E staging column: widen W ({x0 + child_blk_w} > {xe - G})"
fam = "c" if PMEM else "np"
print(f"outline {W} x {H}  core est {core:.0f}  macros {len(ms)}  util_std {A / (W * H - macro_area):.2f}", file=sys.stderr)
json.dump({"W": W, "H": H, "macros": ms, "children": ch}, sys.stdout, indent=1)
