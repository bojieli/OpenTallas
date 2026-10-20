# hcoll_fj3_r128x -- ot_hgi_coll_fj_n2s1_r128 (SAFE q3 COLL parent hard child u_fj, ROWS 128 programme target)

Owner: LEAD3-HBM / HBM-COLLFJ (10-19). Branch claude/collfj-1019 (= issuer v7 branch claude/collq3-iss7-1019 + benches).
RTL change vs the first gate: programme target ROWS 128 sets issuer_start_pc at descriptor accept (e0cf553cf; v7 issuer priming).
Geometry: 90.72 x 86.4 um (1.05:1), util ~42% (FALLBACK of r128w, outline only); pins N (cfg/desc/status), S (issuer), E/W (faults); no macros.
Benches (Verilator 5.050, results/rtl/hbm_coll_fj_1019): parent EQ vs v8x #(AR_ITER 1, ROWS 128) PASS + 3 EQ mutants; fj mutant OT_PT_MUT_LATE_SPC REJECTED.
gate WARN (util 42% < 45% band, rst_q fanout): placement setup +2.1 (fj3) / +5.2 (fj2) ps = no gain over r128w (the margin is logic-bound, not placement) -> NOT submitted; kept as evidence. Next lever if the r128w route misses: flow table -> SRAM / register the assembly/flow decode (item 5).

SAFE-DESIGN checklist:
1 Pins: PASS -- every input registered at its pin in RTL (ot_hgi_coll_fj_core), every output a flop Q, reset landed in 2 registered stages at the face (reset_landing.json).
2 Reach: PASS -- tile < 100 um on a side, no wire near 405 um.
3 Fanout: WAIVED-with-reason -- only the programme-core reset rst_q drives ~301 loads (gate WARN > 256); reset is not a critical cone (2-stage landed, static); same as the earlier hcoll_v5_fj3_r128 RTL.
4 Depth: PASS -- textbook depth ~520-540 ps < 600 ps; no combinational in->out (pin regs).
5 Storage: NOTE -- flow table 128 rows x 18 b (~2.3 kb) stays in flops, read only by the sequential descriptor scan (one row/edge lookahead) and loaded[] bits; ROWS 256 uses SRAM. Borderline vs the ~2 kb guidance; unchanged from the reviewed COLLQ3 SAFE leaf.
6 Floorplan: PASS -- no macros; util ~42% (40-60%), aspect ~1:1, full-width std-cell rows, pin faces <= 6 pins/um, actual pin geometry check all pins on track.
7 Clock: PASS -- one scalar clk, centre-fed tree, pin-flop spread <= 13 ps TT+FF, io_hold_margin 0.03.
8 Schedule: PASS -- static; start_pc written >= ROWS+2 edges before launch, 0 port edges moved (EQ every output every cycle) -> 0 cycles.
