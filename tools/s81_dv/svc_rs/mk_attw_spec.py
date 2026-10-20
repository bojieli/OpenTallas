#!/usr/bin/env python3
"""SVC2: physical/ref_tile/dsdv_svc_rs_attw/spec.json (attw hardened child).  usage: mk_attw_spec.py WT STD_AREA_UM2 [PMEM]"""
import json, math, sys
WT, A = sys.argv[1], float(sys.argv[2]); PMEM = int(sys.argv[3]) if len(sys.argv) > 3 else 1
G = 43.2
BW, BH = 172.8, 41.04           # ot_sram_1r1w_256x256_m2_r2c2
SW, SH = 51.408, 20.79          # ot_sram_1r1w_32x128_m1
big = 16 + 12 + (4 if PMEM else 0); small = 12 + 5 + 4 + (17 if PMEM else 0)
macro_area = big * BW * BH + small * SW * SH
core = A / 0.50 + macro_area * 1.35          # std cells at ~50 % + macros with halo / channel
side = math.sqrt(core)
W = math.ceil(side * 1.15 / G) * G; H = math.ceil(core / W / G) * G
H = max(H, math.ceil((2 * 8 * BH + 3 * G) / G) * G)
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
fam = "c" if PMEM else "np"
print(f"outline {W} x {H}  core est {core:.0f}  macros {len(ms)}  util_std {A / (W * H - macro_area):.2f}", file=sys.stderr)
json.dump({"W": W, "H": H, "macros": ms}, sys.stdout, indent=1)
