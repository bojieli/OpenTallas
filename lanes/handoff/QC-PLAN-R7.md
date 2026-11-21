# QC-PLAN-R7 handoff (2026-11-20 19:4x PST; succeeds QC-PLAN-R6). READ FIRST.

## V1 apply (in progress)
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

## V2 (target apply 11-21 ~20:00)
See section below once started.
