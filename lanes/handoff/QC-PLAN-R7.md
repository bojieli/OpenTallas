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

## Count change on V1 (COORD Q 20:1x; answered in post 5be26ce888)
- 6 signed hc bases split by N_PAD (pcs_e.json) lost their count. Signed with N_PAD 0 (default): sle_hc1__cl22c1ff36, sle_hc2__cl9c4c4509__clf60c5152,
  slw_hc3__clccfc3e6b, slw_hc3__cld86a7ad4 -> all 8 clones are netlist changes, re-sign last. Signed with N_PAD(1): sle_hc0__cl929603c0__cl4baa7c9c,
  sle_hc1__cl7d360508 -> checked (epyc9 qc-plan-r7/inherit, kits PROOF_GEN_RC 0): NOT inheritable: V1 clones add top ports strap_r8pad_u_xh*_a_d/_cid
  and change instance counts (698 vs 900, 2137 vs 697), and inherit_credit needs a current-plan rep. All 6 split bases = re-sign last (12 clones).
- Every other plan type with a signed record is counted, except sle_hc0__cl929603c0__cl38badc56 and slw_sc_v2 (pending archive, unrelated to V1).
- N46C cbn_q00__cldbcda913 a1 route re-run (intel1, started 18:59, class A, CTS -1107): cancel candidate at >3 h (~22:00) via ot-run --cancel <exact unit>, record evidence.

## V2 row families (done 20:4x, epyc9 W=/srv/opentallas-scratch2/claude/qc-plan-r7/v2)
- cb (W/cb: rleg7.sh + r7_cb.py): census HOP cb 63 -> 0; reset legs >300 36 -> 1 on 8 re-dumped types (cbn_q11__cl5cc92dfe local_taps_um added, tool
  still counts needs_local_tap 1); bc_i00/10/30 1->4, nb_i12 3->5; 480 lanes +cycles. OPEN: 12 of 37 tile links 303-356 um (D=4 over 1013-1233 um;
  chain depth intra_dly comes from bind -> needs bind/RTL D 5); cbf_q00_s2, cbf_q01, cbf_q01_s2, cbf_q11 are native RTL (no inst_taps / sites).
- c345 (W/c345): row 5 st_a ctl copies 0 cyc, worst 506-524 -> 310-334 um (u_r3 branch needs +1 stage for 300; flop names unverified vs netlist);
  row 3 cws1/cws2 at N face (0 conflicts) but the 245 ps input delay is a die-wide cbc_rules constant: geometry gives 195.3 ps (cws2) = margin -8 -> +41.7,
  needs a tool patch (per-ring key); row 4 registered reads: defines OT_QC_SWREG (6 st_b types) + OT_TP8S_SRDREG (coll_core), 0 cycles; RTL commit
  b2b7ea1247 on branch claude/qc-plan-r7-v2-srdreg in lane clone W/c345/clone, NOT pushed (bench 13/13; --qfd/--production run oth-ubuntu-564392-1795234394
  was running). Push via ot-push-main before the V2 bind, else the defines are inert.
- r7 (W/r7/r7_hop300.py): knee 523 -> 0 chains over 300; census HOP 510/89 -> 103/53 (63 cb, 40 non-cb that stations do not fix: wide pin window
  end legs incl sle_ctl b_hw_hc1/hc2_o, st_a x_ctl_o 388; 14 per-bit-site rows); 217 ft slots ceil(L/300); 35 sited ft slots still >300 so
  ft_station_max_um stays 405; 876 lanes +1..+8 cycles (worst sl_W*_su_c__x_su_c_su_l0 19 -> 27).
- Compose: W/compose_v2.sh (ot-run, out W/compose_v2.out) -> W/compose/p_v2a.json + side_v2.json + census. Next: push srdreg RTL, strict bind
  (bind_v1.sh pattern with new plan/side, R8 re-derive), LATCHECK, G0, proof GENs (one cbn_q00 kit to CTS for class A), pack/seal/apply as V1.
- CORE-PIN-RELAY-1930 rows: not posted at 20:4x.
