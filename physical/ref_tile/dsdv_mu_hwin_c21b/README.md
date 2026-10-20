dsdv_mu_hwin_c21b -- HWIN21cb gate kit (Claude LEAD2-S81/HWIN2 10-19). Structural successor of the FAILED dsdv_mu_hwin_c21 gate
(0ef6cdd20: post-CTS setup -146 ps at SRAM r_addr_in -- early ra_next = compare -> pointer advance -> next address; FF hold -74 ps /
615 viol mostly at SRAM wd_in; std 8070-8352 um2 = 38.9% of the 54 um band).
RTL change (dsdv_mu_hwin_capture_early_1019.sv + parent dsdv_mu_hwin_capture_1019.sv, both copied byte-identical into the private package sim/):
 - each early-capture SRAM (16 payload, 16 attr, retire) reads from a REGISTER ra_r. Its D = inc(next pointer) under the NEXT limit
   (lm <= decode(lw), so lw_r is the next limit), formed as two candidates from registered pointer/limit state (ra_hold = inc(P),
   ra_adv = inc(inc(P))) with the advance compare only selecting between them. r_addr_in and the read/write hit compare are flop-only cones.
 - the capture register loads the SRAM word only when load_r (registered advance, one kept reset-distinct copy per <=8 bits) is set,
   otherwise holds; same-address writes enter through current_hit. ra_r reset = inc(0) = 1, load_r reset 0 (head is unqualified after reset).
 - Public ABI cycle-exact vs anchor dsdv_mu_hwin 1e057 (EARLY_MITER every cycle): cycles_added 0, no INBOX cycle line owed.
 - NEXT_WRAP_MUTANT in tb_dsdv_mu_hwin_early_capture.sv now corrupts the registered address precompute (ra_after) at the wrap edge
   (the old pb_next wire no longer exists).
Geometry: c21 outline/macros unchanged (model 21cbb79ac, ROOT approved); std band 54 -> 48.6 um, y253.8..302.4 (180 rows), ~46% of band.
Benches (run_c21b_bench.sh, Verilator 5.050): ns47 / ns2 PASS; mutants EC_MUT=2 and NEXT_WRAP_MUTANT FAIL with EARLY_MITER (witnesses
results/rtl/s81_mu_hwin21cb_1019/). Package campaign re-run on the new RTL: core (8 phases), sweeps NS2..10 + NS38..47, four_state NS2.

SAFE-DESIGN checklist (pre-gate; gate packet re-checks 2/3/6/7 on the actual placement):
 1 Pins: PASS -- source-registered pins (ks_q/mc_q/mw_q/rt_q in, c_q/rc_q/t_wf out), keep_pin_regs, reset_landing 2 stages.
 2 Reach: PASS -- macro contacts to the band <= ~374 um (<405) after the band shrink (bottom edge +5.4 um); gate reach census confirms.
 3 Fanout: fixed -- ra_r drives <=4 banks + one comparator per memory; load select replicated per <=8 capture bits (kept, reset-distinct);
   set_max_fanout 32, keep modules non-parameterised (survive Yosys); textbook census on the gate.
 4 Depth: fixed -- c21 critical cones (adv -> pb_next -> r_addr_in, and -> hit_r 603 ps/18 levels) removed: r_addr_in and hit are
   register-to-register; the advance compare now ends in a 2:1 mux at ra_r/load_r D.
 5 Storage: PASS -- 86,016 bits in 84 SRAM macros; capture registers are depth-1 heads, no runtime-indexed flop tables.
 6 Floorplan: fixed -- 43.2 lattice, 10.8 halo, unchanged macro placements; one full-width band now 48.6 um for 40-60% std fill; aspect 1.56.
 7 Clock: gate-checked -- ck/rst_n W pins 271.4-287.4 inside the band; pin-flop spread <= 80 TT+FF; io_hold 0.03. clock_span WARN accepted (spread is the rule).
 8 Schedule: PASS -- static, cycles_added 0 at the public ABI (cycle-exact miter vs anchor).
