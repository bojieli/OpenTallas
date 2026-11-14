# KV-101/PC handoff (2026-11-13, KV-101 sub-lane, DO_NOT_COUNT)

## Verdict
The kv3_pc_v1 650,349 movable count was caused by a silent GPL divergence, not by logic size. **No split for the PC family** (only hub_C splits, per EXPERT-REVIEW-3).
- Original run (E8 /srv/opentallas-scratch2/claude/dkv100-pc-u1-route, 3_3_place_gp.log):
  - Routability-driven GPL ran 5,037 iterations and hit GPL-0089 (it could not reach its target and reverted).
  - HPWL then went from 1.15e7 to 6.9e7 um over iterations 5370-5510.
  - Timing-driven pass 2 (overflow 0.194) then ran repair_design: 393,127 buffers on 119,844 nets, 118,785 of them long wires.
- Movable util was 2.401%, just over the old 2% OT_GPL_SPARSE cut-off, so routability mode stayed on.
- Buffer histogram (epyc8 kv-101/pc/q/hist_orig.log):
  - 84% of 475,533 BUF/INV sit on root nets with 1-2 sinks.
  - 73% sit on roots spanning more than 405 um.
- The same signature appears on S81 dsdv_slice_iq_C t1 (3.08%, 866,785 buffers) and c1x_C t1 (2.86%, 573,207 buffers).

## Fix
- Branch: claude/kv-101-pc-1113@2cea1aa0f3, on origin, worktree epyc7 /srv/opentallas-scratch2/claude/wt/kv-101-pc.
- Change: tools/die_plan/face_flops.tcl sparse default goes from 0.02 to 0.05. Below that util, routability-driven GPL is off; timing-driven stays on.
- Test: tools/die_plan/test_gpl_guard.py gains one test.
- Test results via ot-run on epyc7:
  - test_gpl_guard: 12/12 pass.
  - All face_flops test files: 15 failures, identical to unmodified main.
  - Logs: intel2 ~/kv101log/pc_gpl_guard_tests.log, pc_ff_tests.log, pc_ff_tests_base.log.
- Kits generated before the merge need `export OT_GPL_SPARSE_UTIL = 0.05` in config.mk. KIT-OPS-2 was told this for the kv3_pc_* relaunch and the S81 dsdv C rows.

## Proof
- Run: epyc8 unit oth-ubuntu-2587559-1794620138, kit copy /srv/opentallas-scratch2/claude/kv-101/pc/k_nora, script ../run_nora.sh (env OT_GPL_SPARSE_UTIL=0.03), log intel2 ~/kv101log/pc_nora_place.log.
- After 3_4: 401,992 stdcells minus 108,719 tap/endcap = **293,273 movable**. Preflight projected 290,513.
- GPL took 450 iterations / 1,056 s, and TD pass 2 added only 2,275 net buffers.
- 3_4 placeopt showed 11,664 setup-DRV endpoints. These are advisory here; post-route gates judge them.
- 3_5 DP was still running in the same unit at handoff. Output: k_nora/run/results/.../3_place.odb. It is a private proof; do not count it.

## R-CAP preflight
Main 28cf407973 (kv-rcap-meas merged) already judges this kit on measured synth 227,619, giving TARGET 290,513. No change needed. The receipt is epyc7 kv-101/pc/preflight_main_pc_u1.json.

## Posts
COORD-REVIEW-QUEUE: STATE (coord 129a2ea510), then RESULT + READY (coord 89a0d0850c).

## Not touched
- E7 PC alias constructor PID 3208724.
- The die-kv-100 worktree files.
- No plan/src switch, no cap override.
