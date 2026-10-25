# QC token pass: every MAT family on the bound s8 slice row, all 36 layers + LM + embedding (2026-10-25)

Vehicle: tb_qfd_dv2 FACE 3 = the bound s8 slice row (qfd_dv_slice_die, DV2_S8DIE=1), 12 slices, Verilator 5.050, the
existing fixed-SU-start binary (tok-qw s8exp_wf3, CROM alignment OFF: the MAT families do not use the SU CROM operand
path). Compiler = a725ada856 (codex/s8-mat-1025 code 9737553fe: west L9 receivers 1/3/5, STN pre-arm 20, local-result
guard, LM receivers-only clear). Runner: `run_mat_all.sh` -> tools/qwen_tokfunc/stage_stg_die.sh (pos MAT runlist).
Started by Codex (intel2:/srv/opentallas-scratch2/claude/codex-qc-mat-all-1025, ot-run 60 GB / 24 threads, 2,263 s).

| family | cases | result |
|--------|-------|--------|
| QKV (L0..L35, real fixtures) | 36 | 36 PASS (769/769 words each) |
| GU (L0..L35) | 36 | 36 PASS (3073/3073) |
| O/down (L0..L35) | 36 | 36 PASS (515/515) |
| LM head, full 25 rounds (+ LGPOS framed-AR copy) | 2 | 2 PASS 26/26 (25 amax rounds, gather rank 0, ARX/XC contract) |
| embedding (64 ports) | 1 | PASS 4096/4096 |
| framed-AR (arf) variants | 1 | PASS |
| **total** | **112** | **112/112 = pos verdicts** (`result.json` STG_DIE PASS) |

Negative controls for these families were run on the same compiler in codex/s8-mat-1025 (QKV drop-last-K FAIL 1/769,
LM AMNB5 FAIL 13/26); not repeated here.

## Failed attempt (kept: `result.fail1.json`, `runs.fail1.log`, `lm_bench/lm.fail1.bench.out`)
First run 110/112: both LM cases NO RESULT. Harness bug, not RTL: `lower_lm` lowered the RMSNorm ROOT fields with
`dv_lower.lower()` whose default slice-age record `results/rtl/qlb_c4_1018/dv_lower/slice_ages.json` (the 10-18 slice2
row) is not in the stage tree. Fix (this branch): `lower_lm(..., slice_ages=)` + bench `--slice-ages`; stage_stg_die.sh
passes the vehicle's own `build/slice_ages.json` and fails closed if an lm case has none. Re-run (`rerun_lm.sh`, ot-run
8 GB, intel2 unit oth-ubuntu-3270866-1792927862) used this binary's measured ages (ssq_psum_out 171/187/203, sc_hop 4 =
its slice_calibrate.out). Only the two lm cases were re-run; the other 110 results are the original run.
