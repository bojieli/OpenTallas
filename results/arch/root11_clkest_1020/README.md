# ROOT11 10-20: standard-mode PG bind re-estimates parasitics (EST-0104, PVM9 r6b)

Failure: `pvm9_r6b_4_1_cts.EST0104.log` (HBM-SMATT8, branch claude/hbm-smatt8-pvm-1020 @54ec4f6c1). cts.tcl estimates
placement RC, then `ot_protect_clock_tree` (standard mode) runs `global_connect`, which PG-binds the new CTS cells, and
`repair_timing` stops with `[ERROR EST-0104] inconsistent parasitics state`. Only strict mode re-estimated. The lane's
run-local workaround was a wrapper in its release hook.

Fix (physical/common_flow/clk_net_protect.tcl): standard mode counts connected PG ITerms before and after
`ot_pg_standard_bind`. If the count changed, it re-estimates with the caller's model: `-global_routing` when GRT routes
exist, `-placement` when cells are placed, and nothing on an unplaced design. There is no change when no binding changes,
and strict mode is unchanged.

Test (tools/ref_tile/tests/test_pg_standard_bind.py, real OpenROAD in openroad/orfs:latest, ep5):
- new positive: estimate, then hook, then repair_timing. The log shows OT_PG_STANDARD_REESTIMATE model=placement and
  REPAIR_DONE, with 0 unbound.
- new mutant (re-estimate set to a no-op): reproduces `[ERROR EST-0104] inconsistent parasitics state`.
- result: `cand_pg_tests.out`, 10 passed (incl. test_pg_helper_dependency).

Paired suite (`pytest tools/closure_loop/ tools/ref_tile/tests`, ep5):
- base origin/main: 82 failed, 72 errors.
- candidate: the same set plus the first-draft mutant test, which has since been fixed and passes. NEW failures = 0.
