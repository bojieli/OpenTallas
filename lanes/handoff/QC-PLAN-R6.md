# QC-PLAN-R6 handoff (2026-11-20 ~20:10 PST; succeeds QC-PLAN-R5). READ THIS FIRST. Successor takes V1 to apply.

## V1 plan (green)
- Work dir V = epyc9 /srv/opentallas-scratch2/claude/qc-plan-r6/v1. Base = UNIFY-TOOLS-R3 ph8 (COORD ruling), copies base_ph8_{plan,side}.json, base_r8_ph7.json.
- V1 plan V/p_h.json (sha256 prefix aeae20148627), sidecar V/side_e.json (ca4e6ecf84bb), R8 table V/r8_v1a.json (ea47052e4cdc),
  param split report V/pcs_e.json. Bound tree V/b_n4/tree, launch V/b_n4/launch, bind out V/b_n4/bind.
- Runtime PINNED rt/65f3f85d7c5f = 65f3f85d7c5fa1027622d43ef759816131b43e01 (explicit path; never rt/current; rt_pin.py not landed yet).
  The 10 ledger commits incl 25fc65d0cb1 slew, f02ccd50eb/73717f6992 reset legs, ec16babe0d overlap, b837420ef3d are ancestors.
  Old rt 22a689dfc092 refuses reset.inst_taps (SCHEMA-UNKNOWN-KEY): V1 = re-pin.
- Results: b_n4 strict bind 0 errors; LATCHECK 1921/1921 PASS (V/b_n4/latcheck.json); G0 PASS 0 errors / 530 warnings / 128 types (V/g0_n3, same plan).
  Latency: +1 cycle on 24 rs lanes (c_<s>_bn_00__rsn, c_<s>_bf_00__rsf), +2 on 12 sl_*_ctl__b_hw_ctl_hc2; token impact not simulated (LATCHECK has no tok/s).
- plan_geom_census (rt c113d4e45007 tools/precheck, --tools rt/65f3f85d7c5f/tools/die_plan) on p_h: HOP 510 rows / 89 types (101 > 405, worst cbf_q00 678),
  UNREG_READ? 38 unmeasured; V1 vs A4 0 regressions (ADOPT-CENSUS-1800) = A4 405 um rows -> V2. Rows V/census_ph/ABS-CENSUS.tsv.

## Rows in V1 (compose chain, each script plan_in plan_out report, in V)
b r6_su_c_xsc.py (no-op: ph8 has x_sc_o 3) -> c r6_ctl_hw_hc2.py (sle_ctl__cla4f6f12f b_hw_hc2_o 4->6) + r6_lat_sync.py (latency rows) ->
d r6_su_l_parent_budget.py (12 taps) -> e param_class_split.py --bind-out ph8 bind_r3 (6 head types on N_PAD) ->
a/g r6_st_a_rs.py ... r6_st_a_e3_census.json (11 st_a two-stage rs, 0 cross-row overlaps via r6_st_a_overlap_check.py p r6_kit_istations_main.py) ->
f rleg.sh (reset_leg_plan.py, A4 kit _bound.sv + A4 placed geom, 6 cb types, legs>300 25->1, 0 cycles).
bind_v1.sh = UNIFY bind_core_r3.sh + NO_OVERLAY + PCS_REPORT (clones replace bases in asbuilt internal_stations_types); launch_bind.sh TAG PLAN SIDE RT [schema|-] [no_overlay], env R8=.
NOT in V1: (h) coll_ftc pin regs - the 20 pins are land-ring hold_mux captures rejected as "cone deeper than 6 cells"; regs on 20 bits would skew ring buses.
Fabric option (a) (R5 v1_cbc/r5) is NOT in V1 (base change).

## FABLE-PD-QC-1840 levers
- In V1: st_a two-stage rs (but NOT the 4 control-bit copies, 506-524 um), reset inst_taps on 6 cb types.
- Out (V2, next event): 1 cb tile-link -> u_pc_nk sites + bc_i00/10/30 1->4, nb_i12 3->5 (fabric balance risk, needs strict loop);
  2 RESET-RELAY-GEN-R2 rows for the other cb types + local tap cbn_q11__cl5cc92dfe; 3 sle_ctl cws face home + 245 ps; 4 registered reads coll_core / st_b u_r6;
  5 st_a control copies; 7 300 um pass (510 census rows). Stop list: no route release of the 11 cb rows.

## Cancels (done 19:0x)
- cbx_q10__cl94a12200 A4 a9 (duplicate of a10; geom waiter on epyc7): ot-run --cancel <exact attempt_9 dir> -> 1 client SIGTERM, no container.
- N46C cbn_q00__cldbcda913 a1: no live client (geom PASS, ENQUEUED for route). Needs route-queue removal by WAVE-FLOW / kit_wave_edit, not ot-run.

## Proof GEN (COORD: before re-pin)
- V/proof_gen.sh TYPE (kit-rtl + kit_topology + gen.py phys on b_n4/launch, --src-tree/--rtl-root b_n4/tree). First try failed (src-tree = launch);
  relaunched ~19:05 via ot-run --priority proof --mem 8 --hosts epyc9: sle_st_a_v2__pv4242de79, cbx_q10__cl89936551. Logs V/proof_gen/<type>.log,
  out V/proof_gen/<type>/gen/<type>/config.mk (check PLACE_MAX_TRANSITION line). Optional: one place-only kit of each (Fable 1840 #5).

## Apply steps (successor)
1. Both proof gens PROOF_GEN_RC 0.
2. Pack the 4 changed die files (diff live snap qwen_compute_n46r4_a4 vs V/b_n4/tree: plan_of_record/zz_s29_qc103_s4q9n46r4_final_preview.json,
   qc_start_1106/runtime/{asbuilt_n46r4_final_preview.json, zz_sidecar_n46r4_final_preview.json, zz_r8_s29q103S4Q9N46V0EBQ.json}) with
   rt/65f3f85d7c5f/tools/autopilot src_manifest.py delta-make, then live_tree.py apply --die qwen_compute --pack P --hosts epyc10,epyc2,epyc7,epyc8,epyc9,intel1
   --name qwen_compute_v1r6 --candidate intel2 ~/qc-plan-r3/cand_qc_n46r4_a4_bound.json --out cand_v1.json --event <V1 event>.
3. In cand_v1.json: tools_sha 65f3f85d7c5fa1027622d43ef759816131b43e01, tools_refresh false, smoke detail (strict 0 / LATCHECK / G0 / proof gens).
4. Seal: bind_first (pattern intel2 ~/qc-plan-r3/seal_n46r4_a4.sh) but with R=/srv/opentallas-scratch2/claude/rt/65f3f85d7c5f/tools/autopilot (not rt/current);
   then publish_apply.py apply --candidate cand_v1_bound.json --expect-source <live snap> --expect-event s29q103S4Q9N46R4A4 --lane QC-PLAN-R7.
5. kit_wave_edit: lift hold_items PACKED-BANK (11 st_a), STATION-KNEE (5: sle_ctl x2 -> merged type, su_c x3), CORE-CONTRACT (3 su_l); keep the 11 cb route holds.
6. Post with the census list as known V2 items.
