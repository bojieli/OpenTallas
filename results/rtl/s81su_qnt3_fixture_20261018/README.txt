S81-QNT3 2026-10-18: s81su_full composition gate benches on the COMMITTED fixture tools/s81_suhc/fixtures/su_cases_v2_ildr.pkl
(sha256 8c18c0655ccf6a147cde5e8a65e709ad5ccfd62ba9024e2644019289cd8d2108 = su_gate.CASES_SHA256 = the only fleet copy
ot-epyc4:/srv/opentallas-scratch/codex/s81-hcx-pre-fix-1016/fixtures/su_cases_v2_ildr.pkl).
Source: git archive of 6d627c6fe (tools rtl Makefile physical/asap7_memory_macros_v2 results/rtl/hbm_su_fused_compiler_20261005),
run on ot-epyc5 via ot-run, Verilator 5.050.
m0/run.log: su_gate.py run --shape full --hier          -> RUN full_dpi_m0_a0_h pass (3 x 2413 rows, 0 mismatches)
m5/run.log: su_gate.py run --shape full --hier --mut 5  -> RUN full_dpi_m5_a0_h fail (stale denominator detected)
