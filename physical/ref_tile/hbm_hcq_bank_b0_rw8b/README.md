# hbm_hcq_bank_b0_rw8b -- HC ring bank b0 rw8 (FALLBACK), H.STA.BLK.17.x  (HBM-COLLECT10/COL-HC 10-21)
Top ot_hbm_hc_bankq0_rw8_static (params {"CPO": 1, "DRLY": 2, "WR": 4}).

## Why
HBM-COLLECT10/COL-HC 10-21 b0rw8b: b0_rw6 (339c0ce3a, ep5) CTS FAIL clk_d0 pin-flop spread 175.5 ps TT (1,793 sinks); b0_rw6m clk_d0 147.3 (2,580). Sink dump (3_place): clk_d0 = row-0 assembler h + a at x 145..363 (pulled along the E-face xb_d pins -> SRAM write path) + the weight-pair write copies anchored at BOTH faces (x 164 / 355) + x copies (x 36..146): one root over 330 x 110 um. rw8 RTL (0 added edges, same registers / ages): row assembler split by stage over two regional roots: h on clk_d<r>, a + bad on clk_h<r> (NEW port per row); x write copies on their x SRAM's root clk_x<r>; weight write copies on WR 3 (MAIN) their SRAM pair's read root clk_w<r> / WR 4 (FALLBACK) clk_h<r>. FALLBACK (WR 4).

## Added cycles for the HC ring schedule
0 added edges: same registers, same data, same edges (row assembler h / a / bad, write copies, chain, f relay only change clock root).
RAW0 / HC_MIX_CYCLES unchanged. Die-visible: NEW clock entry ports clk_h0..3 (the die forest delivers them like the other entries).

## SAFE-DESIGN review (safe_1021, 8 points)
1 pins: RTL pin flops unchanged; new ports are clock entries; h->a / a->copy are same-tile glue-root hops (hybrid entries) as before: PASS
2 reach: write path pins->h->a->copy keeps 3 registered hops; pre-existing cross-tile hops unchanged (STA judges)
3 fanout: no new fanout; native census limit 32 in the gate: PASS by construction
4 depth: unchanged: PASS
5 storage: SRAM macros unchanged: PASS
6 floorplan: outline unchanged (die slot), macros on the 43.2 lattice, fill ~48-51 %: PASS
7 clock: clk_d<r> = h only, clk_h<r> = a + bad + weight copies, clk_w<r> = read capture, clk_x<r> = x capture + x copies: each one compact mass; gate --cts
8 reset: unchanged (control/valid only): PASS

## Bench (Verilator 5.050, ot-run): HC_XDEF +HC_BANK_RC +HC_BANK_RW5 +HC_BANK_RW7 +HC_BANK_RW8 (b0/cb/e2 rw8 in the ring)
m0 PASS expected; mut1 / mut5 / mut6 FAIL. Witnesses results/rtl/hbm_hc_ring_1021_rw8.
