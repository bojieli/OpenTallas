# UNIFY-TOOLS-R3 handoff (2026-11-20 ~17:00 PST; succeeds UNIFY-TOOLS-R2)

OWNER priority: class merging tools. Work dir epyc9 /srv/opentallas-scratch2/claude/unify-tools-r3-work (W);
lane clone epyc9 /srv/opentallas-scratch2/claude/unify-tools-r3 (cone tools, rtl, physical/common_flow).

## On main
1. 796b3c1f6ec class_merge prices the representative's OUT kit stations (price_out_stations + late_by_kit; `--reprice-from`).
   On QC ph5 it picks exactly the 5 UNPRICED_KIT_STATIONS lanes (+7 cycles).
2. d4f7c2efd2c pad_hoist re-sites raised ft slots (regs_um / bit_sites_um match the new station count; split_sites puts
   added stages at the longest hop's per-bit midpoint on the existing site grid; `--resite-only`).
3. b837420ef3d pad_hoist --raise-cycles puts each add on lane fixed_cycles (+ row natural/fixed), so G0 latency
   (table == lane_latency) and bind FIXEDCYC (cycles == natural + pad) both hold; landing_contract lets a
   landing_role_strap type leave cland_tstart_in / cland_rstart_in / cland_rstart_out unused (bind ties them 1'b0/open).

## QC private proof chain (base A4+CBX plan_n46cbxm_r4_provider27 + R2 ph5 merges)
- ph6 = ph5 + reprice (5 lanes) + hc3 level-up (+3 on sl_E0/E4/W5_ctl__b_hw_ctl_hc3). R8 re-derived from ph6 bind
  bus_groups: W/r8/r8_ph6.json. ph6/bind_r2 + bind_r3 (re-sited plan_rs): strict 0 errors, LATCHECK 1921/1921 PASS.
- ph6 G0 (g0_r3): schema clean; 41 errors = 25 latency (table-only raises, fixed by 3. above), 15 clock_landings
  (role-strap stm rep moved W2/W4 UP pins: monitor hop 1360 > 405; role-strap unused start pins), 1 geometry
  (sle_st_b x_su_l0_ctl raised 3->5 stations, implicit sites hit a macro).
- ph7 = ph6 re-sited + QC-PLAN-R5's x_sc_o internal_stations (3 stations, 269.8 um; COORD: keep 3) on sle_su_c and
  both slw_su_c, priced: 12 x_su_c_sc lanes +1 (= R5 rows).
- ph8 = ph7 + W/mk_ph8.py (25 lanes: raise moved to fixed_cycles; W2/W4 stm monitor relay groups re-sited, 3 relays
  each on the seam L path) + ft_nudge (st_b slot, 27.4 um slide).
  STATUS: ph8/bind_r3 (R8 W/r8/r8_ph7.json, re-derived after x_sc_o) strict 0 errors, LATCHECK 1921/1921 PASS;
  G0 PASS 0 errors on the same plan (W/ph8/g0_r2b, with main's landing_contract).  g0_r3's 9 errors are only that
  runtime 22a689dfc092's landing_contract predates b837420ef3d (launch tools are read-only hard links: overlay by
  cp to a temp name + mv, never cp onto the link).  plan sha 7d99c48f81db, side 0d6db57a664d, R8 e08c45dffa3a.
  Row file (463 leaf changes vs provider27): W/ph8/rows_ph8_vs_provider27.json (W/plan_row_merge.py delta).
  COORD: ph8 IS the V1 base; QC-PLAN-R6 is the only builder. I answer its ph8 questions.
  G0 runs the runtime 22a689dfc092 launch with main's landing_contract.py copied in.
- Bind recipe: `ot-run --mem 24 --threads 1 --plan-job bind --hosts epyc9 --dir W -- env R8_TABLE=W/r8/r8_ph6.json bash
  W/bind_core_r3.sh PLAN SIDE 22a689dfc092 OUTDIR /srv/opentallas-scratch2/claude/unify-tools-r2-work/overlay/schema_preview.py`,
  then `ot-run --mem 16 --threads 1 --plan-job g0 ... bash .../unify-tools-r2-work/g0.sh OUTDIR/launch G0DIR`.
  Small edits/kits: `OT_RUN_DIRECT=1 ot-run --direct --mem 16 --hosts epyc9` (normal requests queue for hours on epyc9).
- Kit: W/kit/kit_r8.sh LAUNCH KITDIR [TYPE] (kit-rtl with --src-tree <bind>/tree, then gen phys); synth via the
  generated run_kit.sh, then tools/fleet/netlist_inherit.py summary on 1_2_yosys.v.

## Hand to QC-PLAN-R5 (V1 cut ~09:30 PST 11-21)
R5's raw2 plan is on another base (91k leaf diffs), so rows do not carry; rerun the tools on R5's plan:
class_merge x3 (sle_ctl 7->1, role-strap slw_stm, slw_fw; kit pricing inside) -> strict bind -> pad_hoist
--raise-cycles (re-sites) -> ft_nudge -> mk_ph8-style relay re-site for moved stm UP pins -> R8 derive -> rebind ->
G0. Already merged on R5 raw2: W/compose/m3_plan.json + m3_side.json (x_sc_o = 3). Blocked on R5's own bind errors
(EMIT cbn_q00 tile_id stops RTL emit; R8_STALE; TYPE_SPLIT cbn/cbx; slw_stm R8_STRAP_PAD needs r8_strap_pad_max 63)
and on R5 publishing b_hw_hc2_o at 6 stations (compose on top of that file).

## Next
1. Merged kit done: W/kit6b (sle_ctl__cla4f6f12f on ph6/bind_r3; kit-rtl + gen phys + synth OK, FACE_GUARD PASS);
   netlist_inherit summary W/kit6b/ni_summary.json: 149154 cells, 20967 ports, hash 3955adc8bd5c.  prove vs a member
   is not meaningful (members are re-typed to the rep, not inherited); rebuild the kit from ph8/bind_r3 if V1 adopts ph8.
2. Fold the stm relay re-site into class_merge (moved landing pins -> re-relay monitor groups) with a test.
3. Compose on R5 once its plan carries b_hw_hc2_o 6 and its errors clear.
4. S81 leaf class: S81-LEAF-CLASS-1730 owns the floorplan; I support it (findings + extension points posted:
   class_merge MUST_EQUAL ft_slots refusal -> ft-superset mode in merge(); class_window_solve --column after it).
   Do not build S81 rows; fix tool bugs it reports.
- Rule: never rm -rf, even on a wrong path; delete only via ot-delete.
- Merge survey W/try/merge_survey.json: 14 stems merge as-is; rest refused on collector child sites / ft_slots / outline.
- W/plan_row_merge.py is private (3-way leaf merge), not on main.
