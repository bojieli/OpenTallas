# hbm_hcq_bank_e2_rw8b -- HC ring bank e2 rw8 (FALLBACK), H.STA.BLK.17.x  (HBM-COLLECT10/COL-HC 10-21)
Top ot_hbm_hc_bankq_ft_rw8_static (params {"WR": 4}).

## Why
HBM-COLLECT10/COL-HC 10-21 e2rw8b: e2_rw7 / e2_rw7f (ea0b27d35, ot-gold2) CTS FAIL clk_d0 pin-flop spread 301.3 / 212.1 ps TT (1,537 sinks; clk_c / clk_ce now PASS 39.4 / 1.5). Sink dump: clk_d0 = row-0 assembler h + a spread x 31..599 (S-face xb_d pins -> W weight copies AND E x copies) + weight copies at both faces of the W column. rw8 RTL (0 added edges, same registers / ages): row assembler split by stage over two regional roots: h on clk_d<r>, a + bad on clk_h<r> (NEW port per row); x write copies on their x SRAM's root clk_x<r>; weight write copies on WR 3 (MAIN) their SRAM pair's read root clk_w<r> / WR 4 (FALLBACK) clk_h<r>. FALLBACK (WR 4).

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
