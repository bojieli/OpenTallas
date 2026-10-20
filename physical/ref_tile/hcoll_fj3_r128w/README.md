# hcoll_fj3_r128w -- ot_hgi_coll_fj_n2s1_r128 (SAFE q3 COLL parent hard child u_fj, ROWS 128 programme target)

Owner: LEAD3-HBM / HBM-COLLFJ (10-19). Branch claude/collfj-1019 (= issuer v7 branch claude/collq3-iss7-1019 + benches).
RTL change vs the first gate: programme target ROWS 128 sets issuer_start_pc at descriptor accept (e0cf553cf; v7 issuer priming).
Geometry: 82.08 x 77.76 um (1.06:1), util 52%; pins N (cfg/desc/status), S (issuer), E/W (faults); no macros.
Benches (Verilator 5.050, results/rtl/hbm_coll_fj_1019): parent EQ vs v8x #(AR_ITER 1, ROWS 128) PASS + 3 EQ mutants; fj mutant OT_PT_MUT_LATE_SPC REJECTED.
gate (claude/collfj-1019 @d54533489, --cts --remote auto) WARN 0 fail: TT/FF pin-flop spread 12.5/12.5 ps, insertion 149.2/120.5 ps, GRT overflow 0 (M2 52.08%), placement setup WNS +1.2 ps (was +32 at @2f4467de7 -> setup-marginal -> r128x fallback), hold +46 ps; only WARN textbook.high_fanout rst_q 301 loads.

SAFE-DESIGN checklist:
1 Pins: PASS -- every input registered at its pin in RTL (ot_hgi_coll_fj_core), every output a flop Q, reset landed in 2 registered stages at the face (reset_landing.json).
2 Reach: PASS -- tile < 100 um on a side, no wire near 405 um.
3 Fanout: WAIVED-with-reason -- only the programme-core reset rst_q drives ~301 loads (gate WARN > 256); reset is not a critical cone (2-stage landed, static); same as the earlier hcoll_v5_fj3_r128 RTL.
4 Depth: PASS -- textbook depth ~520-540 ps < 600 ps; no combinational in->out (pin regs).
5 Storage: NOTE -- flow table 128 rows x 18 b (~2.3 kb) stays in flops, read only by the sequential descriptor scan (one row/edge lookahead) and loaded[] bits; ROWS 256 uses SRAM. Borderline vs the ~2 kb guidance; unchanged from the reviewed COLLQ3 SAFE leaf.
6 Floorplan: PASS -- no macros; util 52% (40-60%), aspect ~1:1, full-width std-cell rows, pin faces <= 6 pins/um, actual pin geometry check all pins on track.
7 Clock: PASS -- one scalar clk, centre-fed tree, pin-flop spread <= 13 ps TT+FF, io_hold_margin 0.03.
8 Schedule: PASS -- static; start_pc written >= ROWS+2 edges before launch, 0 port edges moved (EQ every output every cycle) -> 0 cycles.
