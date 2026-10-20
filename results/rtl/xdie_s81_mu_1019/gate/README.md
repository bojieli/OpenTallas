# TOK.DS.XDIE.5: XDIE-S81-MU gate collect (S81-TOK4, 10-19 23:10)
Stage: ot-epyc5 `/srv/opentallas-scratch/claude/xdie-s81-mu/stage`, MU release die RTL (mu3 ceaed19c4), Verilator 5.050.
Goldens: `gen_golden.py --gap 100 --dl-model fluid` (guard 1, window 2). Regenerating them locally reproduces the
staged a23r/a46d stim, mu and golden byte-identically.

| run | build | bench | mu_check (window [d-2, d]) |
|---|---|---|---|
| c_g1, c_g1_err | bC MU 0 | PASS 12,096/12,096 | WIN_PASS, INV_PASS |
| a_su | bA MU 2 | PASS 6,044 | WIN_PASS, INV_PASS |
| a_a23r (23 copy-A users, real) | bA | **FAIL**: 139,012 landed, 0 mismatches, 0 faults, tags 29,440/29,440, **708 late** | WIN_FAIL (late 708 at d+1), INV_PASS 23/23 |
| a_a46d, a_a46d_err (46 users, dense) | bA | **FAIL**: 278,024 landed, 0 mismatches, 0 faults, **3,164 late** | WIN_FAIL (late at d+1), INV_PASS 46/46 |
| x_landsel (LAND_MUT_SEL) | bL | PASS (expected: the bench checks only the upper bound) | WIN_FAIL early 4,512: mutant CAUGHT |
| x_stalehd (STALEHD) | bS | still running at 23:00 (the sim has been silent since 17:14 and runs to MAXCYC 1.6M) | pending |
| u (MU 1) | bU | TOKSIM-S81B owns it (out_u2 on ot-epyc7) | pending |

**Finding.** In a23r, the late beats all belong to ONE instance (cand_merge, user 34: 708 beats, each 1 edge late).
In a46d they belong to 11 instances of mixed kinds (idx_topk, mu_hop x4, cand, eng_rows, argmax x2, rows, a_allgather).
- So under dense MU traffic the fluid queue bounds the slot phase to [-1, +2], not [-1, +1].
- The RTL is correct: every beat lands bit-exact, with no fault and every tag in place.
- The compiled deadline (guard 1) is 1 edge too tight. The consumer reads the landing at the deadline, so these
  beats would be missed.

**Fix (schedule only, +1 edge per crossing).** Use `--fluid-guard 2` with mu_check `--win 3`. The 4-slot landing ring
holds a beat 3 edges.
- Expected histograms: su lands at d-3..d-1, the MU runs at d-3..d, and the LAND_MUT_SEL mutant at d-5..d-3, so it
  is still caught.
- With guard 2, the AR phases and the dense users start later (the issues move too), so this needs a fresh sim; an
  offline re-check is not valid.
- `tools/xdie_s81_2/gate_mu_g2.sh out_g2` reruns a/c/x_landsel on the EXISTING builds with `goldens_g2`.
  ot-run unit oth-ubuntu-2049299-1792476102 on ot-epyc5.
- `record_c_g1.json`: per-collective E_meas on MU 0 (a_allgather 573, rows_allgather 739, AR 20480 1232,
  stage_hop 991, ...), as the token_compose input. Recompute it from out_g2/c_g1 once guard 2 passes.
