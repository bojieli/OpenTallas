# TOK-HBM-5 (HBM whole-die token pass, 8 SM; successor of TOK-HBM-4)

## 2026-10-28 22:15 PDT START: base claude/tok-hbm-4-1028@b7c2fe3607, worktree intel2:/srv/opentallas-scratch2/claude/wt/tok-hbm-2. No live jobs inherited. C25b RESULT + bindfull S-role (q0-half) map not posted yet (c25b dir newest 21:59). Polling queue/PATH-HBM; nothing heavy meanwhile.

## 2026-10-28 23:02 PDT PROGRESS (claude/tok-hbm-5-1028@226d7a7346)
- Bench check per COORD FYI (Verilator 5.050 `x <= #d ck`): no intra-assignment delays in any TOK-HBM bench/RTL (results/tok_hbm_*_1028, tools/hbm_next, tools/hbm_b2, rtl/hbm_next) [CHECKED grep]; the whole-die vehicle bench will use none.
- bound_from_plan.py opt-in --side <c25b_side.json> (plan_sha256 must match, fail closed; plan tables win; 8 tests PASS).
- C25b 6b3a80cd + side (22:43): legs down/up NW 40/33 NE 40/34, reset SW/SE/NW/NE 50, root 17 (C25a reset_tree basis, UNCHECKED on C25b), provider<->root 0/0.
  Calendar on real MTP6 jobs: MISSING 10 -> 3: host_to_provider cycles, host_write_interval, plan commit [CHECKED own].
