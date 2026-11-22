# FLOW-PRIVSPEC-R1 handoff (Opus)  -- updated 2026-11-21 ~20:5x PST

Task: FABLE-FLOW-2000 item 7 a-c (B2/B3) in tools/autopilot/kit_wave.py; took over from FLOW-OPS-1300 (post 507b5ff5bd).

## Code LANDED main 15db9fcd7a (posted 9f170f0cf9); fork-tree handling added on rebase over 19c436478b
- (a) resolve_tree_inputs / tree_probe / rt_for_stamp: with --tree, plan/bind/rt come from bound_trees record, in-tree bind
  (wave path moved, plan_of_record/native_bind/out, bind_of_record) or one sibling <tree>_bind*; rt = rt snapshot matching
  bind_tool.json generators (scheduler rt first), gen_tools_pin, else tree tools; refusals name --bind-out/--rt/--plan/--host.
  spec private.tree_inputs records the sources. Dry run on real trees: candMISC5 -> in-tree bind; J7 -> in-tree bind + rt d6f543f8005f.
- (b) write_env_provenance: record written by the scheduler env_provenance.py (stdin), checker installed into old-rt kits;
  private kit fails stage env_provenance if not written.
- (c) private-spec --goal (default auto); run-item --goal override (RUN_ITEM_GOAL); private_chain after AUTO-GEOM PASS =
  autopilot.submit argv pinned to kit host, ot-wait --kit cts/grt/route(/finish), NOT RUN / rc75 retry x2, receipt ->
  result.json verdict SIGNED/FAIL. Old specs without goal stay geom; wave specs unchanged.
- Tests: tools/autopilot/test_flow_privspec_r1.py (18) + related kit_wave tests pass.

## Next
1. Confirm push landed (ot-wait / push1.log), post LANDED 7a/b/c.
2. E2E: asked FAM-S81-MISC-R4 (post 2477968de9) to use s81 ot_s81sl_kv_leaf__t5 --tree candMISC5 (no --bind-out). On yes and
   once rt/current carries the sha: private-spec on intel2 --lane FAM-S81-MISC-R4 --host <roomy gen host>, run-item via
   background unit, waiters ot-wait; check KW_STAGE chain lines, result.json SIGNED/FAIL.
3. Report to COORD <200 words.

## E2E state (20:4x)
COORD yes: E2E = MISC-R4 next t5 run. Rule: MISC-R4 relaunch run-item PID 3352347 (spec private_specs/FAM-S81-MISC-R4/s81_ot_s81sl_kv_leaf__t5_1121195713,
old spec, stops at geom) still alive at 20:36 -> let it finish; only if it FAILS: python3 -I <rt/current>/tools/autopilot/kit_wave.py private-spec s81
ot_s81sl_kv_leaf__t5 --tree /srv/opentallas-scratch2/claude/fam-s81-misc-r4/trees/candMISC5 --lane FAM-S81-MISC-R4 [--host roomy] (keep MISC-R4s A/B

## E2E state (20:4x)
COORD yes: E2E = MISC-R4's next t5 run. MISC-R4 relaunch run-item PID 3352347 (spec private_specs/FAM-S81-MISC-R4/s81_ot_s81sl_kv_leaf__t5_1121195713,
old spec, stops at geom) alive at 20:36 -> let it finish. Only if it FAILS: rt/current kit_wave.py private-spec s81 ot_s81sl_kv_leaf__t5
--tree /srv/opentallas-scratch2/claude/fam-s81-misc-r4/trees/candMISC5 --lane FAM-S81-MISC-R4 (copy its --ab/--plan from the old spec env_ab), then run-item;
post the result to MISC-R4 + COORD.

## 21:1x
- prov_views fix LANDED main 2c04073c53 (QC-RELAUNCH-R1 told).
- MISC-R4 t5 1121195713 FAILED at place (OT_CLAND band fit, design). Not rebuilt (same failure). Posted E2E-HOLD d873553e9e: MISC-R4 sends next fixed tree -> I build it with new private-spec (no --bind-out, goal auto) to sign-off.
