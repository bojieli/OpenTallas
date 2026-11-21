# OPUS-FIX-S81-SVC-R6 handoff (started 2026-11-21 05:0x PST; newest first). Succeeds OPUS-FIX-S81-SVC-R5 (read its STOOD DOWN block).
Nothing signed, nothing exported, nothing pushed to main.

## 11-21 05:2x PST
- chain10d (epyc10 393326) ENDED SPLIT_BAD: "type_split: FAIL sidecar collector row without a tree". Cause (tool, not design):
  type_split write() checks EVERY sidecar collector row for a tree; sidecar_svc_h8_1120 has 130 tree-less base rows (col_h9_r0_p6 pv*,
  serdes__t12, phy__t1, leaf ...). Same check on main (rt/current) -> Codex x_epoch compose 2494448 stopped there too (no sidecar written).
  Fix (private, copy+mv): epyc10 split-hi4-band-test/tools/die_plan/type_split.py checks only split-piece rows (orig: type_split.py.orig-r6).
  Main push via lane clone still owed.
- chain10e: epyc10 PID 622891, opus-fix-s81-svc-r5/bind_hi4x/chain10e.sh (= chain10d, lane R6, log chain10e.log). STATE / KSTATE as before.
  Old: STATE.split2, split2.log.
- REST part kit: epyc8 PID 794204 bind_hi4x/chain_rest8.sh (same path on epyc8): waits epyc10 STATE green -> rsync tree + bind_out3 ->
  prep_rest.py (fresh_kit svc_hi_dsdv_svc_rs__t4 = piece 0) -> place -> route on epyc8. Result epyc8 bind_hi4x/KSTATE_REST, log rest8.log.
- Benches epyc9 2295988 (sims seeds 1,5 running since 13:00 UTC) / 2412579 (prog2 still compiling). Waiters armed (session background loops).
- J7 16-type rows: being built by a worker of this lane in epyc10 opus-fix-s81-svc-r6/j7rows/ (generalized Codex hi4 pipeline).
WAITERS to re-arm (successor): loops on epyc10 STATE (PID 622891), epyc8 KSTATE_REST (PID 794204), epyc9 benches (as R5 W2).
