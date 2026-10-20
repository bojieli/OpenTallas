# HBM-COLLFJ bench record (10-19): fj ROWS-128 leaves after the programme-target change (e0cf553cf)

Source: claude/collfj-1019 @88bed7633 (= claude/collq3-iss7-1019 @9e34ed012 + ptmut bench mode), Verilator 5.050, fleet ot-epyc6 (unpinned ot-run).
Leaves: hcoll_fj3_r128w (ot_hgi_coll_fj_n2s1_r128, q3 u_fj) and hcoll_fj2_r128w (ot_hgi_coll_fj_q2_r128, q2 u_fj).

| bench | q3 | q2 |
|---|---|---|
| run_coll_lp_ars_all.sh eq (SAFE parent with this fj leaf + issuer v7 vs v8x/v8g #(AR_ITER 1, ROWS 128)) | EQ PASS 144,578 | EQ PASS 100,576 |
| EQ mutants refnostep / leafedge / rlaneext | 3/3 REJECTED | 3/3 REJECTED |
| ptmut: fj mutant OT_PT_MUT_LATE_SPC (start_pc only at launch) | REJECTED (program_fault cyc 2441) | REJECTED (cyc 2441) |

Witnesses: witness/m_latespc_{q3,q2}.log. Schedule: start_pc is written >= ROWS+2 edges before launch; the v6 reference reads it only
on start, so no port edge moves (EQ every output every cycle) -> 0 cycles DS / Qwen.

## HBM-COLLFJ2 (10-19 ~00:20): SAFE body ot_hgi_coll_fj_core_s128 / programme_target_s128 (kits hcoll_fj3/fj2_r128s)
Source claude/collfj-1019 @243ff95fd (eq/ptmut) / @3c46cc109 (fjmut) / @ef21342a3 (miter), Verilator 5.050, fleet ot-epyc6 (unpinned ot-run).

| bench | q3 | q2 |
|---|---|---|
| run_coll_lp_ars_all.sh eq (parent with the s128 fj body + issuer v7 vs v8x/v8g with the old fj) | EQ PASS 144,578 (bench/s128_eq_q3.log) | EQ PASS 100,576 |
| EQ mutants refnostep / leafedge / rlaneext | 3/3 REJECTED | 3/3 REJECTED |
| ptmut OT_PT_MUT_LATE_SPC (s128) | REJECTED (witness/s128_m_latespc_q3.log) | REJECTED |
| fjmut OT_PT_MUT_LA_STALE (s128: SRAM read + loaded lookahead frozen) | REJECTED (witness/s128_fjmut_q3.log) | REJECTED |

Random beyond-contract miter (run_coll_pt_s128_miter.sh, tb_hgi_coll_pt_s128_miter.sv): s128 == programme_target #(ROWS 128) PASS 956,173
cycles, 3,000 episodes (300 configured, 387 starts, 2,668 faults, 8 frames on the drain-completion edge) -- bench/s128_miter_pass.log;
mutants LDH_NOFWD (contract-unreachable in the parent programme: 55-edge host gap) and LA_STALE REJECTED (witness/s128_miter_*.log).
Schedule: 0 port edges moved -> 0 cycles DS / Qwen.
