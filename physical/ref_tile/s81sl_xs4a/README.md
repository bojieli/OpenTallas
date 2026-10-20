# ot_s81sl_xs4 kit (S81-XG4XS; xs half of S81.STA.LEAF.5 s81sl_xg) -- SAFE checklist (pre-gate)
Source claude/s81-xg4xs-1020 @2b29d00d6+; xs4_equiv vs main ot_s81sl_xs + 1-edge relay: base PASS, 6 mutants FAIL (Verilator 5.050, ep7, witnesses results/rtl/s81_slice_1019/xg4xs/).
1 Pins: source-registered (one capture flop per input bit, kept capture copies for control; outputs leave flops); reset 2-stage landing (reset_landing) + 2 sync -> 39 regions.
2 Reach: 864-um-wide leaf; gate native reach audit decides (no single-cycle wire > 405 um owed).
3 Fanout: kept copies / one-hot selects (see spec structural_change); mapped native32 census runs in the gate (FAIL = gate FAIL).
4 Depth: registered one-hot read-mux lines into stage-3 AND-OR; gate textbook depth decides.
5 Storage: 3.84 kb exponent flop array moved to 6 SRAM 128x64; data in 24 SRAM 128x256 + 7 ROM 4096x72.
6 Floorplan: 37 macros on the 43.2 lattice, row/column channels per spec macro_channel; full-width std band between macro rows.
7 Clock: CTS root at the S face (OT_CKKM_K 16 k-means sinks); pin-flop spread <= 80 TT+FF judged by the gate; io_hold_margin 0.03.
8 Schedule: static; +1 edge vs main xs (input relay) handed to MU.S81.CAL with the rs half's +1 edge/stop.
xs4a = 604.8-um outline (45.3-um row channels), xs4b = 518.4 (23.7-um row channels): parallel variants, bind the first CLOSED.
