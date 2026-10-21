# hbm_hcq_bank_cb_rw8b -- HC ring bank cb rw8 (FALLBACK), H.STA.BLK.17.x  (HBM-COLLECT10/COL-HC 10-21)
Top ot_hbm_hc_bankq_rw8_static (params {"CPI": 1, "CPO": 1, "WR": 4}).

## Why
HBM-COLLECT10/COL-HC 10-21 cbrw8b: cb_rw6 / cb_rw6m (339c0ce3a, ep5) CTS FAIL clk_c pin-flop spread 127.4 / 127.9 ps TT (263 internal sinks). Sink dump: chain cd/cv wraps lane leaf g0 (W channel x 8..43 at the d_* pins + S strip y 6..43 at the o_* pins), taps cv[3..8] / cd[*][27] dragged to x 185, fin_q / f_o relaying f_in (NW) -> f_out (SE) at (188, 230). rw8 RTL (0 added edges, same registers / ages): row assembler split by stage over two regional roots: h on clk_d<r>, a + bad on clk_h<r> (NEW port per row); x write copies on their x SRAM's root clk_x<r>; weight write copies on WR 3 (MAIN) their SRAM pair's read root clk_w<r> / WR 4 (FALLBACK) clk_h<r>. cb: FQR 1 = fin_q / f_o on their own 2-sink root clk_f (NEW port); the cv / cd chain fenced (dbRegion, released before DPL/CTS by tools/landed_parent/lp_fence_release.tcl) beside the d_* / o_* pins: MAIN SW corner box, FALLBACK W-channel box at the d_* pins. FALLBACK (WR 4).

## Added cycles for the HC ring schedule
0 added edges: same registers, same data, same edges (row assembler h / a / bad, write copies, chain, f relay only change clock root).
RAW0 / HC_MIX_CYCLES unchanged. Die-visible: NEW clock entry ports clk_h0..3 + clk_f (the die forest delivers them like the other entries).

## SAFE-DESIGN review (safe_1021, 8 points)
1 pins: RTL pin flops unchanged; new ports are clock entries; h->a / a->copy are same-tile glue-root hops (hybrid entries) as before: PASS
2 reach: write path pins->h->a->copy keeps 3 registered hops; cb f relay 3 hops over ~1,460 um on its own root; chain taps -> per-row copies <= ~600 um (pre-existing, STA judges)
3 fanout: no new fanout; native census limit 32 in the gate: PASS by construction
4 depth: unchanged: PASS
5 storage: SRAM macros unchanged: PASS
6 floorplan: outline unchanged (die slot), macros on the 43.2 lattice, fill ~48-51 %; chain fence box 10.8..42 x 86.4..178.2 (released before DPL/CTS): PASS
7 clock: clk_d<r> = h only, clk_h<r> = a + bad + weight copies, clk_w<r> = read capture, clk_x<r> = x capture + x copies, clk_c = fenced chain, clk_f = fin_q/f_o: each one compact mass; gate --cts
8 reset: unchanged (control/valid only): PASS

## Bench (Verilator 5.050, ot-run): HC_XDEF +HC_BANK_RC +HC_BANK_RW5 +HC_BANK_RW7 +HC_BANK_RW8 (b0/cb/e2 rw8 in the ring)
m0 PASS expected; mut1 / mut5 / mut6 FAIL. Witnesses results/rtl/hbm_hc_ring_1021_rw8.
