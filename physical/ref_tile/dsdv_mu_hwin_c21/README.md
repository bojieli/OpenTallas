dsdv_mu_hwin_c21 -- HWIN21c gate kit (Claude LEAD2-S81/MU 10-19). Structural successor of the failed
dsdv_mu_hwin_cb route/gate (1e057b7bf: TT -371 ps, 9 broad roots, 93 macro pairs > 405 um, macro slew 503/526 ps).
RTL: private capture package dsdv_mu_hwin_capture_1019 (source 9e7921b40 on branch codex/s81-hwin-private-package-1019,
receipts cbbc9e161 / de061577f) with EARLY_HEAD_CAPTURE=1: payload/attr/retire SRAMs read the NEXT head address one
edge early (ra_next) with qualified previous-write forwarding, so macro Q -> compare gets its own registered stage.
Public ABI cycle-exact vs the anchor dsdv_mu_hwin 1e057 (EARLY_MITER every cycle): 276 legal + 276 expiry receipts
over all 46 shapes, core 136/136, NS2 four-state terminal 0, NS47 four-state phases 0-5 PASS (6-10 live at gate time).
Geometry: model 21cbb79ac (ROOT 13:45 accepted / 13:46 selected): 388.8 x 604.8 (+7.69%), 84 ot_sram_1r1w_64x16 on the
43.2 lattice (placements = model.json, generate path g_early), one full-width std band y248.4..302.4 (54 um).
Benches (run_c21_bench.sh, Verilator 5.050, same tb/defines as the package): ns47 / ns2 PASS; mutants EC_MUT=2 and
NEXT_WRAP_MUTANT FAIL with EARLY_MITER (witnesses results/rtl/s81_mu_hwin21c_1019/, from core02 on ot-epyc7).

SAFE-DESIGN checklist (pre-gate; gate packet re-checks 2/3/6/7 on actual placement):
 1 Pins: PASS -- source-registered pins (ks_q/mc_q/mw_q/rt_q in, c_q/rc_q/t_wf out), keep_pin_regs, reset_landing 2 stages.
 2 Reach: fixed -- early capture adds a registered stage after each macro; max macro contact to band 368.7 um (<405); gate PNG/reach census confirms.
 3 Fanout: gate-checked -- set_max_fanout 32, keep modules renamed to dsdv_mu_hwin_capture_1019_* (non-parameterised, survive Yosys); textbook_lint census on the gate.
 4 Depth: PASS -- the SRAM-Q -> compare cone is split by the early capture register (was the -371 ps path).
 5 Storage: PASS -- 86,016 bits in 84 SRAM macros; capture heads are depth-1/2 bundles, no runtime-indexed flop tables.
 6 Floorplan: PASS -- 43.2 lattice, 10.8 halo, channels >= 20 um, std 50.4% of the band (priced), aspect 1.56, one full-width band.
 7 Clock: gate-checked -- ck/rst_n W pins at the band centre (y271-287); pin-flop spread <= 80 TT+FF; io_hold 0.03. clock_span WARN (>600 um outline) accepted: macro sinks only, spread is the rule.
 8 Schedule: PASS -- static, cycles_added 0 at the public ABI (cycle-exact miter vs anchor); no INBOX cycle entry owed.
