#!/usr/bin/env python3
"""S81-KITS-RTLC 10-24 ruling (b) step 2: also drop vd[0] (rst copy; bk_g never reads it: unused input, producer = a
dsfd_selt_c rst flop with no other reader of the pin).  Packed vd (367) = {vd[512:502], vd[356:1]}."""
import sys
R = sys.argv[1] + "/rtl/dsrom_sys/s81_dv/unit/bk/"
def sub(f, a, b, n=1):
    s = open(R + f).read(); c = s.count(a)
    assert c == n, (f, a[:70], c)
    open(R + f, "w").write(s.replace(a, b))
g = "dsdv_bk_g.sv"
sub(g, "dsfd_selt_c word {vd[512:502], vd[356:0]} (368 bits); vd[513] (kind msb) and vd[501:357] are constant 0 at\n"
       "    // the producer (ot_s81ph_sel_tile.sv o_d kinds 3/4/5/7) and are not pins.  VD_PK = 0: legacy 514-bit vd.",
       "dsfd_selt_c word {vd[512:502], vd[356:1]} (367 bits); vd[513] (kind msb) and vd[501:357] are constant 0 at\n"
       "    // the producer (ot_s81ph_sel_tile.sv o_d kinds 3/4/5/7) and vd[0] (rst copy) is never read here: not pins.\n"
       "    // VD_PK = 0: legacy 514-bit vd.")
sub(g, "input  wire [(VD_PK ? 367 : 513):0] vd,", "input  wire [(VD_PK ? 366 : 513):0] vd,")
sub(g, "assign vdu = {vd[367:357], 1'b0, 145'd0, vd[356:0]};", "assign vdu = {vd[366:356], 1'b0, 145'd0, vd[355:0], 1'b0};")
sub(g, "assign vdu = {1'b0, vd[367:357], 145'd0, vd[356:0]};", "assign vdu = {1'b0, vd[366:356], 145'd0, vd[355:0], 1'b0};")
c = "dsdv_bksel_c.sv"
sub(c, "output wire [367:0]     vd    // S81-KITS-RTLC 10-24: packed {vd[512:502], vd[356:0]} (dsdv_bk_g VD_PK)",
       "output wire [366:0]     vd    // S81-KITS-RTLC 10-24: packed {vd[512:502], vd[356:1]} (dsdv_bk_g VD_PK)")
sub(c, "assign vd = {vdw[512:502], vdw[356:0]};             // vdw[513], vdw[501:357]: constant 0 (dropped pins)",
       "assign vd = {vdw[512:502], vdw[356:1]};             // vdw[513], vdw[501:357]: constant 0; vdw[0]: unread (dropped pins)")
for f in ("dsdv_bk_sel.sv", "dsdv_bk_sel_x.sv", "lp/dsdv_bk_sel_x_lp.sv"):
    sub(f, "wire [367:0] vd;", "wire [366:0] vd;")
print("ok")
