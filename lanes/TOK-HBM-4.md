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
