#!/usr/bin/env python3
"""DIE-S81-80 11-08: contract LEF of the bksel SPLIT logic child ot_s81ph_hq_pk2 (W inputs, E outputs, clk S centre).
M4 face pins every second M4 track (0.096 um), centred on the face; clk M5 0.024 x 0.084 (the hist_n24 lesson: no
2-track clk rect)."""
import sys
W = H = 194.4
OFF_Y, OFF_X = 0.012, 0.108
ins = [("rst_n", 1), ("i_ingc", 6), ("i_flc", 6), ("c2_vc", 6), ("c2_flc", 6), ("i1_s_dc", 288), ("c3_sel_dc", 288),
       ("i0_lane", 592), ("c2_p", 592)]   # PINCOPY: one pin per P capture flop
outs = [("pi_vp", 6), ("pi_fl", 1), ("pi_bv", 1), ("pi_lv", 16), ("ps_vp", 6), ("ps_fl", 1), ("ps_bv", 1), ("ps_lv", 16),
        ("pi_line", 592), ("ps_line", 592)]
def bits(lst):
    r = []
    for n, w in lst:
        r += [n] if w == 1 else [f"{n}[{i}]" for i in range(w)]
    return r
def ys(n):
    span = (n - 1) * 0.096
    k0 = round(((H - span) / 2 - OFF_Y) / 0.048)
    k0 += k0 % 2
    return [round(OFF_Y + 0.048 * (k0 + 2 * i), 4) for i in range(n)]
pins = []
bi, bo = bits(ins), bits(outs)
for n, y in zip(bi, ys(len(bi))):
    pins.append((n, "INPUT", "M4", (0, y - 0.012, 0.084, y + 0.012)))
for n, y in zip(bo, ys(len(bo))):
    pins.append((n, "OUTPUT", "M4", (W - 0.084, y - 0.012, W, y + 0.012)))
xc = round(OFF_X + 0.048 * round((W / 2 - OFF_X) / 0.048), 4)
pins.append(("clk", "INPUT", "M5", (xc - 0.012, 0, xc + 0.012, 0.084)))
assert all(4.32 < p[3][1] and p[3][3] < H - 4.32 for p in pins if p[2] == "M4"), "pins inside the face margin"
o = ["VERSION 5.8 ;", 'BUSBITCHARS "[]" ;', 'DIVIDERCHAR "/" ;', "UNITS", "    DATABASE MICRONS 1000 ;", "END UNITS", "",
     "MACRO ot_s81ph_hq_pk2", "  FOREIGN ot_s81ph_hq_pk2 0 0 ;", "  CLASS BLOCK ;", f"  SIZE {W:g} BY {H:g} ;"]
for n, d, L, r in sorted(pins):
    o += [f"  PIN {n}", f"    DIRECTION {d} ;", "    USE SIGNAL ;", "    PORT", f"      LAYER {L} ;",
          "        RECT  " + " ".join(f"{v:.4f}".rstrip("0").rstrip(".") if v else "0" for v in r) + " ;", "    END", f"  END {n}"]
o += ["END ot_s81ph_hq_pk2", "", "END LIBRARY", ""]
open(sys.argv[1], "w").write("\n".join(o))
print(len(bi), "in", len(bo), "out, clk x", xc, "W y", ys(len(bi))[0], "-", ys(len(bi))[-1])
