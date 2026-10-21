#!/usr/bin/env python3
"""HBM-DBK9 2026-10-21: pin plan of the OUTPUT-LANDED dbk_cpl parent (hv16_dbk_cpl_o1 / _o1b): the l1 plan
(assigned_pins_l1.tcl, every existing port unchanged) + the four face output roots clk_out[k] in the middle of the output
groups they clock: [0] S x 132 (wd banks 3 | 0, S x 2-262), [1] S x 415 (gap between wd bank 1 and wd bank 2, S x 264-523),
[2] N x 132 (wd banks 4 | 5), [3] N x 398 (wd bank 6 | wb_* x 400-430 | wd bank 7).  Nearest free track (0.012 + 0.048 k)
with >= 2 tracks of clearance on the same layer and face (same rule as make_pins.py).  python3 make_pins_o1.py SRC OUT"""
import re, sys
SRC, OUT = sys.argv[1], sys.argv[2]
PITCH, OFF, CLEAR = 0.048, 0.012, 0.096
ADD = {"clk_out[0]": ("M5", "S", 132.0), "clk_out[1]": ("M5", "S", 415.0),
       "clk_out[2]": ("M5", "N", 132.0), "clk_out[3]": ("M5", "N", 398.0)}
pat = re.compile(r"ot_assigned_pin_exact \{(\S+)\} (\S+) (\S) ([\d.]+)$")
lines = open(SRC).read().splitlines()
used = {}
for l in lines:
    m = pat.match(l)
    if m:
        used.setdefault((m.group(2), m.group(3)), []).append(float(m.group(4)))
for name, (lay, face, tgt) in ADD.items():
    occ = used.setdefault((lay, face), [])
    k0 = round((tgt - OFF) / PITCH); hit = None
    for d in range(0, 4000):
        for k in (k0 + d, k0 - d):
            p = round(OFF + k * PITCH, 3)
            if all(abs(p - q) >= CLEAR - 1e-6 for q in occ):
                hit = p; break
        if hit is not None:
            break
    occ.append(hit)
    lines.append(f"ot_assigned_pin_exact {{{name}}} {lay} {face} {hit:.6f}")
    print(f"{name} {lay} {face} {hit:.3f} (target {tgt})")
lines[0] = ("# HBM-DBK9 hv16_dbk_cpl_o1: exact pin plan = l1 plan + clk_out[3:0] face output roots "
            "(results/arch/hbm_dbkcpl_land_1020/make_pins_o1.py); ODB readback mandatory.")
open(OUT, "w").write("\n".join(lines) + "\n")
