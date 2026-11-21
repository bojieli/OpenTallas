# QC-PLAN-R7 handoff (2026-11-20 19:4x PST; succeeds QC-PLAN-R6). READ FIRST.

## V1 APPLIED 11-20 19:5x (event s29q103S4Q9N46R6V1, receipt lanes/handoff/qwen_compute_atomic_apply_1795233764725085687.json)
- Seal: strict 0, LATCHECK rc 0, bind qwen_compute_v1r6_bind_1120193410 on 6 hosts, matches 128/128. 19 holds lifted (549764a938e).
- Census (epyc9 /srv/opentallas-scratch2/claude/qc-plan-r7/census_v1, script ../census_v1.sh): ABS HOP 510/89 types (worst 678 cbf_q00__cl1b5a6458), UNREG_READ? 38; EVENT-CENSUS REGRESS 0/128; ADOPT-DIFF LAG 237, BOTH 50, ledger 0 missing.
- Not done: publish_gate PASS record (advisory warning), source guard not ready (advisory).
- Proof GENs PASS (epyc9 V=/srv/opentallas-scratch2/claude/qc-plan-r6/v1/proof_gen): sle_st_a_v2__pv4242de79, cbx_q10__cl89936551 PROOF_GEN_RC 0, PLACE_MAX_TRANSITION 320.
- Pack: epyc9 /srv/opentallas-scratch2/claude/qc-plan-r7/pack_v1 (make_v1.py there; copy at intel2 ~/qc-plan-r7/pack_v1): 4 die files from V/b_n4/tree
  (plan aeae20148627, sidecar ca4e6ecf84bb, asbuilt cf0f2400edbc, r8 ea47052e4cdc) + 172 tools files of rt/65f3f85d7c5f differing from live A4 manifest b4d7f328b637.
- live_tree apply -> /srv/opentallas-scratch2/claude/kw45/snap_qwen_compute/qwen_compute_v1r6 manifest 80e4b0c40e09 on epyc10,epyc2,epyc7,epyc8,epyc9,intel1.
- Candidate intel2 ~/qc-plan-r7/cand_v1.json: event s29q103S4Q9N46R6V1, tools_sha 65f3f85d7c5f... (top + config), config.tools_refresh false,
  review_before_route items = 10 class-A cb types (V1 event).
- Seal: intel2 ~/qc-plan-r7/seal_v1.sh (bind_first with pinned rt) -> seal_v1.log / seal_v1.rc -> cand_v1_bound.json.
- Then: publish_apply.py (rt/65f3f85d7c5f) apply --candidate cand_v1_bound.json --expect-source .../qwen_compute_n46r4_a4 --expect-event s29q103S4Q9N46R4A4 --lane QC-PLAN-R7 --no-bind-first --no-post-bind
- After apply: kit_wave_edit unset the 19 hold_items (11 PACKED-BANK st_a, 5 STATION-KNEE, 3 CORE-CONTRACT); keep the 11 cb holds.
  Then plan_geom_census / event_adopt_diff / event_census on the applied tree and post counts.

## Holds added by R7 (kit_wave_edit)
- 65f9eaf04c5: hold_items cbn_q00__cldbcda913 (N46C a1 CTS -1107 class A). Its N46C a1 route run was re-admitted 18:59 on intel1 (run_kit route,
  unit kw-qwenco-cbnq00cldbcda913-1-41017; earlier run SIGTERMed 11:41 at GRT repair -925). Admitted units are not touched by holds; it qualifies for
  the >3 h unsignable cancel at ~22:00 (evidence: CTS -1107 / GRT -925 / 83 endpoints, Fable 1840 sec 3).
- 8cd505347e7: hold_items on the other 10 class-A cb types (Fable 1840 stop list). stops_off makes route_hold_items inert, and after the switch the A4
  event review gate no longer covers A4 rows, so hold_items is the only thing that keeps them off route. Release on V2 apply.

## V2 (target apply 11-21 ~20:00): compose on epyc9 W=/srv/opentallas-scratch2/claude/qc-plan-r7/v2
- Base W/base_v1_plan.json (= V1 p_h aeae20148627), side/r8 copies beside it. Tools pinned W/rt_pin.txt = rt/cca022294010 (rt_pin.py --export).
- Row families (each a plan_in plan_out report script, composed in order cb -> c345 -> r7):
  W/cb   cb family: fix 1 tile-link sites + bc_i 1->4 / nb_i12 3->5, RESET-RELAY-GEN-R2 item (3) inst_taps for 11 cb types + cbn_q11__cl5cc92dfe local tap, cb 300 um hops.
  W/c345 fix 3 sle_ctl cws face home + 245 ps, fix 4 registered reads coll_core / st_b u_r6, fix 5 st_a ctl copies.
  W/r7   fix 7 300 um pass, non-cb chains (knee300.tsv need_limit) + routed rows + ft slots.
- CORE-PIN-RELAY-1930 rows: not posted yet at 19:5x; fold in when posted.
- Then: plan_geom_census on the compose, strict bind (V1 bind_v1.sh pattern, NO_OVERLAY=1), LATCHECK, G0, proof GENs, pack/seal/apply like V1.
