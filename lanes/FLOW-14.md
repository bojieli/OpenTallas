# FLOW-14 (successor of FLOW-13) — handoff written 2026-10-31 01:27 PDT

## Merges pending (ROOT-MERGE-AH)
- claude/flow-13-1224-1031@23efaa444 (APPROVED COORD 01:2x): OWNER 12.24 optimistic RCX + 12.24b/c nominal die STA + setup unc 0 + margin_report.py.
- claude/flow-13-1224fu-1031@2c36bd79d (READY, contains 23efaa444): COORD 10-31 decisions 1-3 (landing window T/2, die_sta/die_ci 0, KV chain OCV 0, 3 die kit gens 0, make_block_sdc 0, AGENTS.md).
  Check: git merge-base --is-ancestor 2c36bd79d origin/main.

## Tag cuts (yours)
1. DONE 02:1x by FLOW-13: flow-20261031-a-s81 @95b1992a3 (tag ae1f4c9347f), canary NO-REGRESSION; NOTE the canary design stopped at post-CTS insertion gate (FAIL_POSTCTS, slice_station__t12) so S81 sign-off metrics were NOT REACHED -- if the b-s81 canary stops there too, ask S81 owner whether FAIL_POSTCTS is design or flow before tagging.
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

## OWNER RULE 12.25 (queue 01:5x) — die clock gate = routed PAIR SLACK, not skew (FLOW-14 item, with test)
- die_sta_related (summary/gate verdict), the freeze-gate tools (die_infra.py checks ~l.1052-1065 read tt_setup/ff_hold_margin; any die gate wrapper that reads die_sta_related) and ~/coord/tools/release_tree_plan.py must report PASS/FAIL on:
  (a) worst TT setup slack >= 0, (b) worst FF hold slack >= +10 ps, (c) block arrival-contract violations = 0.
- Related-pair skew > 150 ps (tools/budgets/common.py SKEW_INTER_PS and wherever the 150 ps related-pair verdict is computed) becomes WARN only, never FAIL.
- Pair slacks are the routed DRT+RCX arrivals under the 12.24c nominal policy (die_sta_related --margin-policy nominal default; FF hold keeps 25 ps uncertainty).
- Test: a fixture with skew 200 ps but setup >= 0 / hold >= 10 / 0 contract violations -> PASS + WARN; hold +9 -> FAIL; one contract violation -> FAIL. READY ROOT-MERGE (release_tree_plan = coord tool, commit via coord-commit.sh after review).

## ITEM (SIGNOFF-SPRINT-10 2026-10-31 01:47 PDT): release_tree_plan record pins read from the KIT INPUT pins.json, not the routed DB -> HBM ring_ag miscounted
- Symptom [CHECKED cache 01:29]: plans/hbm/plan_of_record/d44c design_unmatched ot_hfd_coll_q2_hard_v8g__ring_ag: 'moved pin 1 e.g. clk (M5, 116568, 233280) vs plan (M5, 116664, 116640)', record intel1:/srv/opentallas-scratch2/claude/signoff-sprint-3/ring_f (RE-SIGN flow-20261030-f-hbm, LEC EQ), pins_path = intel1:/srv/opentallas-scratch2/claude/hbm-cores-kits-27/ring_wl120/pins.json (kit INPUT: clk at the N edge).
- Truth [CHECKED SIGNOFF-SPRINT-9 22:44 + 23:09, pincmp on the routed DB]: routed_db .../ring_wl120/run/results/asap7/hbc_ot_hfd_coll_q2_hard_v8g__ring_ag/base/6_final.(odb|def) has clk PLACED/FIXED at (116664 116640) = plan centre; 2228/2228 plan pins (d44c cores/..._c25c_centerclk.json, pins_sha c9210b65) within 0.2 um; outline 233.28^2. The 12 mp_isl* extra ports are declared die-owned FT (core_die_owned_ft.v1 = ..._die_owned_ft.json), same as the counted collar.
- Code: ~/coord/tools/release_tree_plan.py REC_PINS_PY (~l.582-600) reads (1) the face_guard key = kit pins.json, (2) <kit>/pins.json, and only (3) <record dir>/*.lef when both are gone. The kit input pins.json is what the flow was ASKED to place, not what it placed (here the kit's pin placer moved clk to the plan centre per the centerclk plan).
- Fix request: when the record names routed_db (PROVENANCE resign) or a 6_final.def/odb beside the record, read pins from the routed DEF (or the signed abstract LEF) FIRST; kit pins.json only as a last fallback, and say which source was read in the 'read' field. Accept declared core_die_owned_ft.v1 ports as extras. Test: fixture record whose kit pins.json differs from its routed DEF -> pins taken from the DEF, design matched.
- Expected effect: HBM 1/84 -> 2/84 designs (ring_ag). Owner: FLOW-14 (shared coord tool; SIGNOFF-SPRINT-10 does not patch the counter). DEFAULT until fixed: SIGNOFF-SPRINT COUNT lines quote HBM 2/84 CHECKED.
- 2026-10-31 02:14 PDT CLAIM [FLOW-14] successor of FLOW-13 (parked 02:13). First: fix sha on top of 2c36bd79d8d for the 3 ROOT-MERGE-AH HOLD test fails (hbm test_hbm_static_ids UNC_SETUP_PS 60, KV test_kv_related_clock landing 356.666), then b-<die> tags, OWNER 12.25 slack gate, seam_landing 0, ring_ag pins source, R2route verdict.
