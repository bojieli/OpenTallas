# MU-ADOPT-SLICE2 witnesses on the SLICE-E tree (claude/mu-adopt-slice-e-1019 @e258bea48)

Fleet ot-epyc4, Verilator 5.050, script `eq_one.sh` (sources listed inside; run as `bash eq_one.sh OUT CASE` from the repo root).

| case | what | result |
|---|---|---|
| eq0 | qfd_dv_slice2_e (SU_LT 1, HD_W130 1, MU_NU 4) == regenerated landed re-cut qfd_dv_slice2_e_lpf (MU_NU 4), random stimulus, 98,373 compares | PASS |
| eq3 | same, OT_LPF_MUT3 (ag bits swapped) | FAIL (1,447 mismatches), as wanted |
| eq1 | same, OT_LPF_MUT1 (heads fault lost), random mode | PASS: MUT1 is observable only in +hronly mode (SLICE-E's own witness bench_eq1/eq1h) |
| b2 | dv_bench2 f j m o on the HEAD slice (-GSU_LT=1 -GHD_W130=1 -GMU_NU=4) | f 3/3, j 3/3, m 8/8 (4 users, chunked heads), o 2/2 PASS |

Bench m failed (2/8, every token = the largest head so far) before the root-merge fix: qfd_dv_scalar2 MU_NU > 1 now restarts
the root's argmax merge on the token edge (see ../README.md on claude/mu-adopt-slice-1019).
NOT run here (owed by OWN-QWEN/SLICE-E with the lp.py rerun): lp lockstep (qfd_dv_slice2_e_lpf_lp) at MU_NU 4, +quiet / +hronly eq modes.
