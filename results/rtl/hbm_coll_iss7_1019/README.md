# HBM-COLLQ3-V7 bench record (10-19): 128-row COLL issuer v7 (SRAM loop tables)

Source: claude/collq3-iss7-1019 @e0cf553cf, Verilator 5.050, fleet (ot-epyc6, unpinned ot-run).

| bench | result |
|---|---|
| run_issuer_v7r128_miter.sh pos 3 600 (core v7_r128 vs v6 #(ROWS 128) + leaf m128v7 vs issuer_m #(ROWS 128)) | PASS 1,478,710 edge checks, 1,800 launches, 110,327 non-zero iterations, 359,815 uops from rows >= 64 |
| miter mutants reload / nofwd / swap | all REJECTED (witness/miter_*.log) |
| run_coll_lp_ars_all.sh q3 all (parent with this leaf vs v8x #(AR_ITER 1, ROWS 128), v6 issuer) | EQ PASS 144,578; EQ mutants 3/3 REJECTED; RS PASS + 3/3 REJECTED; LP audit PASS, unland FAIL, MUT0 PASS, MUT1/2/4 FAIL |
| run_coll_lp_ars_all.sh q2 all (vs v8g) | EQ PASS 100,576; same mutant / RS / LP results |

First parent EQ at @d3db1f2a9 FAILED (program_fault cyc 2441): the ROWS-128 programme target set issuer_start_pc only at
launch, so the v7 lookahead was never primed (constraint (a)); fixed in e0cf553cf (start_pc at descriptor accept, as
ROWS 256). Logs of the failing run: lanes/PL-COLLQ_logs/collq3v7_*.log (coordinator dir).

Schedule price: 0 added edges on any issuer port (miter is every-edge exact) -> 0 cycles/token DS and Qwen.
