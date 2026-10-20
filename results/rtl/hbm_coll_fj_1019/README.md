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
