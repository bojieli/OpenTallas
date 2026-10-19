# s81dvbk_g2 (dsdv_bk_g) -- kit g2km, S81-BKG-CLK 10-19

Re-CTS of the CLOSED view s81dvbk_g2-g2lv-b3ca6169e (TT +17.62 / FF +6.55) whose native audit fails the clock rule
(pin-flop spread TT 90.0 / FF 84.2 > 80). Analysis: results/arch/s81_svcbk_1018/bkg_clk_spread_b3ca6169e.json.
Change: clock_split_km.tcl (K 12 regional roots on the pin-flop ring around the SRAM stack), io_hold_margin 0.03.
Same RTL, outline 216 x 172.8, macros, pins. reroute_reason native_spread.

## Safe-design checklist (owner 10-19)
1. Pins: PASS -- source-registered (inputs land in vstop / strap / vd pin flops, outputs leave vin / vstop / vout flops; pin_regs off with reason). rst_n lands in the 2-stage synchroniser rs[1:0] (gate reset_landing: 2 sinks, ok).
2. Reach: PASS -- 216 x 172.8 tile, every hop < 405 um.
3. Fanout: WAIVED-with-reason -- rs[1] async reset drives 642 flops (lint WARN): async assert, recovery/removal closed at TT/FF in the closed route; a per-region relay is an RTL change of a closed block (parents colv/selv benches) and is not the failing item. Data cones: dsdv_bk_live x4 kept per lane (native launch fix f92c5b837).
4. Depth: PASS -- closed route TT +17.62, gate depth within budget; no combinational in->out (native audit comb 0).
5. Storage: PASS -- 2 x ot_sram_1r1w_128x256 macros; no runtime-indexed flop arrays > 2 kb.
6. Floorplan: PASS -- macros on the lattice (one abutted N-S stack, at_exact pitch 41.088), W/E halo 10.8, W/E channels 60 um, N/S 43.2 um, aspect 1.25, full-width std-cell bands; trial GRT 0 on geometry 2.
7. Clock: FIXED -- regional k-means roots (this kit); target pin-flop spread <= 80 TT+FF with margin for routed RC (+~20 ps measured); io_hold_margin 0.03.
8. Schedule: PASS -- no RTL / cycle change.
