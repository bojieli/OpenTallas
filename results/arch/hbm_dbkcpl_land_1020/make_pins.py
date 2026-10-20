#!/usr/bin/env python3
"""HBM-HC7-DBK 2026-10-20: exact pin plan of the LANDED dbk_cpl parent (hv16_dbk_cpl_l1 / _l1b) from the s1/s2 plan
(results/arch/hbm_die_v16_d4f/dbk_cpl_1017/assigned_pins.tcl @ca6707526).  Only 9 ports move:
  rr valid of lane b (rr[b*257+256]) from the W face centre (y 250.0-252.2) to the face point beside bank b's write_en pin
  (W y = bank top for the column-0 banks and bank 1, S x 446 for bank 2, N x 273 / 446 for banks 6 / 7), so the bank-side
  landing copy is <= ~280 um from both and the controller copy sits half way (relay_anchor.txt);
  rst_n from E y 2.4 (the SE corner) to E y ~195 (beside clk_rst, nearest the reset relay station at the cluster centre).
Every new position is the nearest actual track (0.012 + 0.048 k um, the measured grid of the plan) with >= 2 tracks of
clearance from every other pin on the same layer and face.  python3 make_pins.py SRC OUT"""
import re, sys
SRC, OUT = sys.argv[1], sys.argv[2]
PITCH, OFF, CLEAR = 0.048, 0.012, 0.096
MOVE = {  # port -> (layer, face, target um along the face)
    "rr[256]":  ("M4", "W", 130.7),    # bank0 write_en (100.5, 130.7)
    "rr[513]":  ("M4", "W", 150.0),    # bank1 write_en (273.3, 130.7); W group of bank 1's data (86-170)
    "rr[770]":  ("M5", "S", 446.1),    # bank2 write_en (446.1, 130.7)
    "rr[1027]": ("M4", "W", 260.3),    # bank3 write_en (100.5, 260.3)
    "rr[1284]": ("M4", "W", 389.9),    # bank4 write_en (100.5, 389.9)
    "rr[1541]": ("M4", "W", 519.4),    # bank5 write_en (100.5, 519.4)
    "rr[1798]": ("M5", "N", 273.3),    # bank6 write_en (273.3, 519.4)
    "rr[2055]": ("M5", "N", 446.1),    # bank7 write_en (446.1, 519.4)
    "rst_n":    ("M4", "E", 195.0),    # beside clk_rst (E 190.0)
}
lines = open(SRC).read().splitlines()
pat = re.compile(r"ot_assigned_pin_exact \{(\S+)\} (\S+) (\S) ([\d.]+)$")
used = {}
for l in lines:
    m = pat.match(l)
    if m and m.group(1) not in MOVE:
        used.setdefault((m.group(2), m.group(3)), []).append(float(m.group(4)))
out, done = [], {}
for l in lines:
    m = pat.match(l)
    if m and m.group(1) in MOVE:
        name = m.group(1); lay, face, tgt = MOVE[name]
        occ = used.setdefault((lay, face), [])
        k0 = round((tgt - OFF) / PITCH)
        for d in range(0, 4000):
            hit = None
            for k in (k0 + d, k0 - d):
                p = round(OFF + k * PITCH, 3)
                if all(abs(p - q) >= CLEAR - 1e-6 for q in occ):
                    hit = p; break
            if hit is not None:
                break
        occ.append(hit); done[name] = (lay, face, hit, float(m.group(4)), m.group(3))
        out.append(f"ot_assigned_pin_exact {{{name}}} {lay} {face} {hit:.6f}")
    else:
        out.append(l)
out[0] = ("# HBM-HC7-DBK hv16_dbk_cpl_l1: exact pin plan = s1 plan @ca6707526 with rr valid beside each bank and rst_n beside "
          "clk_rst (results/arch/hbm_dbkcpl_land_1020/make_pins.py); ODB readback mandatory.")
assert len(done) == len(MOVE), set(MOVE) - set(done)
open(OUT, "w").write("\n".join(out) + "\n")
for n, (lay, face, p, old, oface) in done.items():
    print(f"{n:9s} {oface} {old:8.3f} -> {lay} {face} {p:8.3f}")
