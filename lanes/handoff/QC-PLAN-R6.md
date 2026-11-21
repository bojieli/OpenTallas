# QC-PLAN-R6 handoff (2026-11-20 ~17:50 PST; succeeds QC-PLAN-R5)

## Base (COORD ruling 17:3x): UNIFY-TOOLS-R3 ph8, NOT the R5 raw2/fabric (a) plan
- Work dir epyc9 /srv/opentallas-scratch2/claude/qc-plan-r6/v1 (V). base_ph8_plan.json / base_ph8_side.json / base_r8_ph7.json = copies of
  unify-tools-r3-work/ph8 plan.json, side.json, r8/r8_ph7.json (ph8 bind_r3 strict 0, g0_r3 rc 0).
- The R5 fabric option (a) line (v1_cbc/r5, q1-q3) is NOT in V1 now. q3 result (for reference): R8_STALE/PARAM_REGEN gone, 9 errors:
  4 bn/tn TYPE_SPLIT (root cause: option (a) raised cw_s* with no native chain -> bn receiver pad +2; fix r5/r6_cws_native.py),
  4 head-pad PARAM splits, 1 EMIT tile_id (follows a split). q4 cancelled (base change).

## Compose chain in V (each script: plan_in plan_out report)
1. r6_su_c_xsc.py (row b): ph8 already has x_sc_o 3 stations on 3 su_c types -> no change (p_b.json).
2. r6_ctl_hw_hc2.py (row c): merged sle_ctl__cla4f6f12f b_hw_hc2_o 4 -> 6 stations (~269 um), 12 sl_*_ctl__b_hw_ctl_hc2 lanes fixed 5 -> 7 (p_c.json).
3. r6_su_l_parent_budget.py (row d): 12 u_lane core taps on sle_su_l0__cl7a55c676, slw_su_l0__cl1a1c1f8f, sle_su_l1__cl5ea486db SIGNED -> parent_budget (p_d.json).
4. param_class_split.py (row e, tool from ph8 bind_r3 launch, --bind-out ph8/bind_r3/bind): 6 types split on head N_PAD
   (sle_hc0__cl929603c0__cl4baa7c9c, sle_hc1 x2, sle_hc2__..clf60c5152, slw_hc3 x2) -> p_e.json + side_e.json (pcs_e.json).
5. r6_st_a_rs.py p_e p_f rep_f r6_st_a_e3_census.json (rows a+g): rs_s0/rs_s1 two stages on 11 st_a types, one occupancy map,
   24 rs lanes (c_<s>_bn_00__rsn, c_<s>_bf_00__rsf) fixed 5 -> 6. r6_st_a_overlap_check.py p_f.json r6_kit_istations_main.py
   (main ec16babe0d cross_row_site_overlaps): TOTAL 0. Open: 4 control bits per type fan out to u_r0-3/x_st_b_o, worst leg
   506-524 um (needs last-stage copies or R3 move); rs_s1 25-61 bits at 300.2 um (lattice rounding).
## Strict binds (launch_bind.sh TAG PLAN SIDE RUNTIME [schema|-] [no_overlay]; bind_v1.sh = UNIFY bind_core_r3.sh + NO_OVERLAY)
- b_s1: p_f on rt 22a689dfc092 (ph8 runtime). b_n1: p_f on rt 65f3f85d7c5f (= rt/current, re-pin probe, no overlay/schema preview).
  Results V/b_<tag>.log/.rc, V/b_<tag>/bind/bind_report.json, latcheck.json. Then G0 (UNIFY g0.sh pattern on the launch dir).
## Still to do
- (f) cb* reset legs: geom dumps of 9 placed A4 cb* kits running (epyc2/7/9 /srv/opentallas-scratch2/claude/qc-plan-r6/gd/<type>/geom.tsv,
  gd.sh = RESET-RELAY-GEN recipe). After the V1 bind: rt/current tools/die_plan/reset_leg_plan.py PLAN TYPE <V1 bind>/rtl/<type>_bound.sv GEOM OUT REP
  per type (form R; macros skipped). No hand rows.
- (h) coll_ftc 20 unregistered pins (A4 auto_geom: ard_wo_in_data_i[63+64k], arl_wo_in_last_i...): pin-side register rows. My recompute
  (unreg.py) without the kit's exempt sets gives 5133, not usable; use geom_rules.metrics with the kit args.
- Re-pin QC tools to rt/current after one proof gen of a bound type (COORD); slew limit is the gen default (25fc65d0cb1), no die_gen_env key.
- Apply: G0 + strict 0 + LATCHECK green -> publish_apply (intel2 ~/qc-plan-r3/apply_n46r4_a4.sh pattern), lift kit_wave holds PACKED-BANK (11 st_a),
  STATION-KNEE (5), CORE-CONTRACT (3) via kit_wave_edit, post.
