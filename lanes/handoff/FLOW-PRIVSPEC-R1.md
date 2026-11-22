# FLOW-PRIVSPEC-R1 handoff (Opus)  -- updated 2026-11-21 ~20:5x PST

Task: FABLE-FLOW-2000 item 7 a-c (B2/B3) in tools/autopilot/kit_wave.py; took over from FLOW-OPS-1300 (post 507b5ff5bd).

## Code (commit 52bcb72f66 in clone intel2:/srv/opentallas-scratch2/claude/FLOW-PRIVSPEC-R1/clone; push via ot-run -> ot-push-main, log ../tmp/push1.log)
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
