# CTRL rg2 n32s: parallel FALLBACK of n32r (REFILL-0325/FALLBACK, 10-20; owner lane S81-LINK4)

Owner rule 10-19 (parallel fallbacks, bind the first to close). Same RTL, defines, mapped netlist, benches and
witnesses as s81ctrl_rg2_n32r / s81ctrl_rg2_native32 (RTL byte-identical, branch claude/s81-link4-1020 @aa7060689);
only the outline height, the request-SRAM y origin and the N-face pin y change. Kit = ref_tile gen of
physical/s81_ctrl_rg2/spec_n32s.json (all other kit files identical to n32r apart from names/FH/macro y).

Structural difference vs n32r: outline 388.8 x 324 (the native32 height, so the die slot height is unchanged);
R0 request SRAMs y 172.8 -> 194.4, so the full-width mid std-cell band grows 29 -> 50.5 um (room for the
2956 FF, CTS buffers and hold repair between the N/S pin-flop rows; n32r placement hold -22 ps pre-repair).

SAFE checklist (pre-gate):
1. Pins PASS: every pin registered in RTL in its own domain (pin_regs opt-out reason unchanged); reset_landing 2 stages.
   Pins = n32r x/order/layers (dsfd_ctrl_rg2_n32s_pins.tcl), N face y 324; 3.3 pins/um (<= 6).
2. Reach PASS (to verify post-GRT): tile half-perimeter 712.8 um (n32r 691, native32 855 had the 411 um reset pairs);
   SRAM payload legs unchanged in x, request legs to the N face unchanged (N channel 28.9 um as n32r).
3. Fanout PASS (mapped netlist unchanged): 2956 FF / 4 SRAM, max 31 loads, 0 drivers >32 incl. reset; PRE-GATE NATIVE
   census = n32r in-gate census PASS max31 (aa7060689) on the identical netlist; the gate re-runs it in-flow.
4. Depth PASS: textbook 293.4 ps; n32r placement setup +309 ps.
5. Storage PASS: 4 x 16x340 dual-clock SRAM FIFOs, no >2 kb flop arrays.
6. Floorplan PASS/WARN: macros 2x2 at x 43.2/216.0, y 43.218(R180, same track waiver as n32r)/194.4 (43.2 lattice);
   channels W 41 / mid-x 58 / E 56 um, mid band 50.5 um full width; fill 38% (WARN, macro-dominated, as n32r 40%); aspect 1.2.
7. Clock PASS (to re-measure): K8 regional core roots + hclk split unchanged; n32r clk 46.3/47.9, ckh 44.6/40.9 TT/FF;
   io_hold_margin 0.03.
8. Schedule PASS: no RTL change, 0 added edges.
Die: same width as n32r, +21.6 um height = native32 height (no die slot change vs native32).
