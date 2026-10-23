#!/usr/bin/env python3
"""STW-S81c-COLLA4-LEP 10-22 (lep_mu_h w16): f_host S-face pin WINDOW beside the RX SRAM column.

  fh_window.py W15_relay_place.txt m|f LO HI > relay_place.txt

w15m / w15m2 / w15f / w15f2 --cts gates (TT placement RC) all fail ONE class: macro->reg f_host (-20.1 / -39.0 / -17.4 /
-16.2 ps).  Per-path dump (w15m2 4_1_cts ODB): RX lane-0 SRAM rd_out pins sit on x = 613.0 (bank b at y 45 + 43 b), the
f_host pins were balanced over S x 1.4..476.5 in bit order, so bank 0/1 bits (f_host[0..255]) ran 450-610 um west to
their pin flops: f_host[4] rd_out[7] (613.0,45.3) -> flop (9.8,3.9) -39.0, f_host[127] bank1 (613,88) -> (97.4,7.7) -36.5.
Boxing the flops on their pins (w15 rev2) made it worse (-20.1 -> -39.0): the pins themselves are too far.
Fix (zero latency, no RTL / port / protocol change): spec pin_ranges put f_host on S x [LO, HI] (under the RX column,
two pin layers M3+M5 via pin_balance) and f_ks / t_host / t_kd on disjoint ranges west of it; every f_host bit's pin is
then <= ~250 um Manhattan from its rd_out pin.  This script drops the w15 rev2 f_host boxes (old pin x) and re-boxes the
f_host launch flops FIRM on the S face over their NEW pins (uniform balanced pin model x_i = LO + (i + 0.5)(HI - LO)/515),
MAIN 32-bit groups y 4-10, FB 16-bit groups y 3.5-7.5; released before DPL (relay_chain_release.tcl) as in w15 rev2.
"""
import sys

base, mode, lo, hi = sys.argv[1], sys.argv[2], float(sys.argv[3]), float(sys.argv[4])
N = 515
out = [l.rstrip("\n") for l in open(base) if not l.startswith("re+:^u_ot_pr_core\\.u\\.f_host")]
out.append(f"# fh_window.py {mode}: f_host pins S x {lo:g}..{hi:g}, launch flops boxed over them (STW-S81c-COLLA4-LEP)")
G = 32 if mode == "m" else 16
fy0, fy1 = (4.0, 10.0) if mode == "m" else (3.5, 7.5)
px = [lo + (i + 0.5) * (hi - lo) / N for i in range(N)]
for g0 in range(0, N, G):
    g1 = min(N, g0 + G)
    xa, xb = max(2.5, px[g0] - 1.5), min(645.5, px[g1 - 1] + 1.5)
    alt = "(" + "|".join(str(i) for i in range(g0, g1)) + ")"
    out.append(f"re+:^u_ot_pr_core\\.u\\.f_host\\[{alt}\\]\\$ {xa:.2f} {fy0:.2f} {xb:.2f} {fy1:.2f}")
print("\n".join(out))
