# FLOW-14 (successor of FLOW-13) — handoff written 2026-10-31 01:27 PDT

## Merges pending (ROOT-MERGE-AH)
- claude/flow-13-1224-1031@23efaa444 (APPROVED COORD 01:2x): OWNER 12.24 optimistic RCX + 12.24b/c nominal die STA + setup unc 0 + margin_report.py.
- claude/flow-13-1224fu-1031@2c36bd79d (READY, contains 23efaa444): COORD 10-31 decisions 1-3 (landing window T/2, die_sta/die_ci 0, KV chain OCV 0, 3 die kit gens 0, make_block_sdc 0, AGENTS.md).
  Check: git merge-base --is-ancestor 2c36bd79d origin/main.

## Tag cuts (yours)
1. flow-20261031-a-s81 @95b1992a3: intel2 /srv/opentallas-scratch2/claude/flow-canary/runs/s81_95b1992a3_1031_000709_104242 was still in 5_1_grt at 01:27. Cut only on NO-REGRESSION (canary.py verdict), tag message = run dir + verdict, as the a-qc/a-kv/a-hbm/a-head tags (lanes/FLOW-13.md 00:07/00:37).
2. AFTER 2c36bd79d (or 23efaa444) is on main: new tag per die flow-20261031-b-{qc,kv,hbm,head,s81} @ that main sha, each only when its flow-canary run on a main sha containing it is NO-REGRESSION. Expect canary deltas to be POSITIVE setup slack (setup unc 60->0 in re-sign) — that is the policy change, not a regression; hold must be unchanged. COORD 10-31 confirmed: the setup-slack jump 60->0 is EXPECTED, not a regression; HOLD MUST NOT MOVE (any hold delta = real regression, no tag). If canary.py flags the setup jump, record it as policy (OWNER 12.24c) in the tag message.
3. Then announce in COORD-REVIEW-QUEUE: die owners re-sign routed DBs on the b-tags (memory: RE-SIGN same routed DB, kind:resign PROVENANCE.json) and run margin_report.py core/die-clock per die -> lanes/MARGIN-REPORT-<die>.tsv.

## Open items
- TODO (COORD 10-31 approved, 12.24c intent): tools/die_plan/seam_landing.py:41 planner setup estimate 833-60 -> 833-0 (also docstring line 11); test + READY ROOT-MERGE.
- OWNER 12.24 RCX timing delta on real trees UNCHECKED: first clock_routed / rcx_kv / ot-clk mesh rec rebuild per die should report latency/skew vs previous (R_sq/w) basis.
- margin_report die-clock mode never run on a real proof yet (mock-tested only); core mode smoke CHECKED intel2 S81 dp_hd_turn_a (min period 884.56 ps).
- Old hardcoded 60 left (budget math, not sign-off): physical/common_flow/link_budget_consistent.sdc, rebudget_measure.sdc, tools/budgets/common.py:21, core_infra_sta.py:148, proto_sweep.py:136.

## Probes (FLOW-13 R2route = PRD route-keep fix e79f6e789, merged 8eba511155a)
- epyc2 /srv/opentallas-scratch2/claude/flow13-probe/R2route: DRT iter 32, 255 violations at 01:27 (R1 control flow12-probe/R1route stalled 628 @ iter 52). Waiter post_R2.sh writes flow13-probe/CHAIN.txt (DRC/TT/FF). Compare vs P8eco TT +306.81 / FF +7.44 / DRC 0. If DRT does not reach 0, the route-keep keeps 25627 wires but the 999 ripped nets + 689 changed instances still overload the hotspot x15-17 y10-15 um: next step = shrink the rip set (only nets touching changed instances) before end_incremental.
- After reading CHAIN.txt: delete epyc2 flow13-probe and flow12-probe (both mine/handed to me) and intel2 flow12-pinx.

## Rules
Shared flow changes -> READY ROOT-MERGE; never touch main; tests with each change; tags >= 2x/day.
