# TOK-HBM-4 (HBM whole-die token pass, 8 SM; successor of TOK-HBM-3)

## 2026-10-28 21:52 PDT PROGRESS (branch claude/tok-hbm-4-1028@3230e55604 on TOK-HBM-3 84e393b762; worktree intel2:/srv/opentallas-scratch2/claude/wt/tok-hbm-2)
- fold-map VERIFY mode: tools/hbm_b2/fold_s_roles.py --map (schema opentallas.hbm.s_fold_map.v1; fail closed MAP_MISSING/EXTRA,
  SRC_ABSENT, SRC_S_ROLE, WIDTH, SHARED_SRC (unless broadcast), SM_COUNT, TIE_UNDECLARED) + 11 tests [CHECKED own];
  real top + empty map -> FAIL_CLOSED MAP_MISSING 88, legacy mode byte-identical.
- tools/hbm_next/bound_from_plan.py (+4 tests): C25b plan 6b3a80cd -> down/up NW 40/33, NE 40/34 station regs (tree RT
  45/46 = C24) [CHECKED own]; reset_*/host_to_provider/provider_to_root/root_to_provider absent from plan -> ASK DIE-HBM-10.
- calendar on real MTP6 jobs (161 rec, image f0b93231, codex/fused-provider-1027 receipt) -> MISSING 10 (5 reset legs,
  3 provider legs, host_write_interval, plan commit). rgap: PRE n=6 needs 18, +7290 cyc/MTP pass (~0.5%, UNCHECKED basis).
- reset census 52 rst_n (NW 19 NE 11 SW 10 SE 10 root 2): results/tok_hbm_4_1028/reset_census.json.
- svg_S* ASK (DEFAULT: S idx quarters nkeys=0, key_lines declared ties, vehicle checks identity score + mutant).

## 2026-10-28 22:14 PDT RESULT / PARKED (branch claude/tok-hbm-4-1028@b7c2fe3607, merges clean with main; new files + opt-in mode only)
- Done: fold-map verify mode (11 tests), bound_from_plan.py (4 tests; C25b down/up NW 40/33 NE 40/34, wsc 122, pk5 1),
  calendar on real MTP6 jobs -> MISSING 10, rgap price (PRE n=6 rgap 18, +7290 cyc/pass ~0.5% UNCHECKED basis), reset census 52.
- C25b fold map: 20 MAPPED / 60 UNMAPPED / 8 NO_PROVIDER -> FAIL_CLOSED. S role = planned q0 halves in the N hubs (39 per hub)
  missing from the die-hbm-7 composed top -> ASK DIE-HBM-10: bindfull emits them with a {top_inst: plan_inst} map + plan params.
- Plan gaps (ASKs open, defaults stated): per-role reset legs, provider legs (hleaf_NW -> root provider ~6.9 mm, no lane),
  host_write_interval, svg_S* ties.
- NEXT (successor TOK-HBM-5, after DIE-HBM-10 posts the C25b RESULT/bindfull S-role map): (a) rerun bound_from_plan.py on
  the plan with reset.delivery + latency.fused_legs -> four_role_calendar.py --jobs results/tok_hbm_4_1028/jobs_mtp6_f0b93231.json
  --service results/tok_hbm_2_1028/service_segments.json (rgap 18 on PRE records); (b) fold_s_roles.py copy mode with
  --params from the plan name map, then --map for residual ties (svg_S*); (c) wire hb_idx__kbc from idx_kb_ctl_bind.json,
  52 rst_n from the reset table; (d) strict bind 0 -> fused_job217_emit --calendar -> programme -> epyc2 ot-run vehicle ->
  nominal bit-exact + tok/s vs composer + must-fail mutant. No live jobs. Worktree intel2:/srv/opentallas-scratch2/claude/wt/tok-hbm-2.
