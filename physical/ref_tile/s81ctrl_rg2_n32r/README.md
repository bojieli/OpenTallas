# CTRL rg2 n32r: SAFE re-floorplan of native32 (S81-LINK4, 10-20)

Same RTL, defines and mapped netlist as s81ctrl_rg2_native32 (source 808c23b00 RTL byte-identical; only the
outline, macro origins and pin plan change), so the native32 mapped census and benches carry over unchanged.
Reason: native32 gate 013001 WARN0FAIL was a physical HOLD -- fill 28.1% in an over-sized 531.25x324 outline,
two thin N/S face bands, and 7 reset FF->FF pairs >405 um (max 411.4, hrbank q0 -> PC1 u_wd) across the wide tile.

SAFE checklist (pre-gate):
1. Pins PASS: every pin registered in RTL in its own domain (pin_regs opt-out reason unchanged); reset_landing 2 stages.
   Pin plan = native32 order/layers, x rescaled onto the 388.8 face and snapped to each layer's track
   (physical/s81_ctrl_rg2/dsfd_ctrl_rg2_n32r_pins.tcl); N 1246 / S 1245 pins over 380 um = 3.3 pins/um (<= 6).
2. Reach FIXED (geometry): tile width 531.25 -> 388.8 removes the 411 um reset pairs' span; SRAM payload legs were
   max 302.7 um in the wider tile and only shorten. Verify after the gate with the post-GRT reach audit.
3. Fanout PASS (mapped, unchanged netlist): 2956 FF / 4 SRAM, max 31 loads, 0 drivers >32 incl. reset (Codex 9a18d68df).
4. Depth PASS: gate textbook 293.4 ps; placement path classes +285 ps slack in native32.
5. Storage PASS: 4 x 16x340 dual-clock SRAM FIFOs, no >2 kb flop arrays.
6. Floorplan FIXED: outline from synthesis area (macros 46117 + std 1308 um2) -> 388.8 x 302.4 (9 x 7 cells of 43.2),
   fill 40.3%, aspect 1.29; macros 2x2 at x 43.2/216.0, y 43.2/172.8 (43.2 lattice); channels W 41 / mid 58 / E 56 um
   (macro side faces carry the pins: R0 rd W / wd+mask E, R180 swapped), row channel 29 um = full-width std band
   joining the N/S pin-flop rows. Waiver: R180 response macros sit at y 43.218 -- the only on-track origin for a
   flipped 100.71 um macro (best_shift +0.018 um); a literal 43.2 bbox would put every pin off the M4 tracks.
7. Clock PASS (to re-measure): unchanged K8 regional core roots + hclk split; native32 measured clk 59.1/62.2,
   ckh 35.2/38.6 TT/FF; io_hold_margin 0.03.
8. Schedule PASS: no RTL change, 0 added edges.
Die: tile centred in the 531.25 PHY-pitch slot; S-face seam offset <= ~71 um (die refit by S81-MU6 GEN).
