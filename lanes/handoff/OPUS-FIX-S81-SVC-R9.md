# OPUS-FIX-S81-SVC-R9 handoff (started 11-21 18:4x PST; successor of OPUS-FIX-S81-SVC-R8). Nothing signed yet.
Read R8 handoff (lanes/handoff/OPUS-FIX-S81-SVC-R8.md) for J7/J8 history and FABLE-PD-S81-2000 (lanes/FABLE-PD-S81-2000.md) for the hi4 diagnosis.

## Rulings in force
- COORD 19:3x: hi4 macro candidates DROPPED; lever = cut window order by endpoint + drop dead cut bits; NO 4th place run on the old cut list; no settings changes.
- ft3 t1/t6: centre re-site only (done).

## Done (all posted)
- J8 svc PLAN epyc2 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r9/j8_rows/plan_ftresite_r9.json (sha 24dbfb31) = R8 ed6d6287 + 2 ft3 rows (ft3_entry_rows.json). Posted to S81-J6-ASSEMBLY-R5 (no ack seen yet).
  FILE lines ALSO need epyc10 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r8/j8/scoped_h8_overlay/{s81_svc_r8_j8_sources/, physical/die_plan/s81/bind/inputs/map_svc_j8_scoped_h8.json}; asbuilt base must be the tree root (posted).
- Dead cut bits: RTL part wrappers tied spare plan bits (Q_p 4663, Y_p 276, attnh_o0 247, Y_p_2 119, Q_p_2 79, rinv 1, vid_o0/rsv_i0 lanes). census_x_r9.json (epyc2 r9/pre) sizes census to the bound.
- main type_split spec cut_window_pref, pushed main 1b0a7d73 (lane clone intel2 r9/repo).
- hi4 re-split on J8 (epyc2 r9: pre/gen_hi4_j8pre.py -> j8base/plan_pre_j8.json; spec_r9.json; split_r9.sh; repair_ft_grid.py) -> j8base/split_hi4x/plan_c_ftgrid.json. Cut pins 13409 -> 8022; windows Q_p 90-240, attnh_o0 242-597 (3 seg), attn_i0 425-575, attn_o1 712-729, Y_p 755-905, attn_o0 908-1129, Q_p_2 1492-1648. FT 5630 unique sites, hops <= 391.
- Gate tree intel2 /srv/opentallas-scratch2/claude/opus-fix-s81-svc-r9/treeJ8 (real copy of sealed J7 a6771d121e95 minus results/ + overlays: R8 hi4 RTL (ovl_hi4), J8 seven-layout files (j8base split dir onto s81/), scoped_h8 sources + reprove41 (ovl_j8)). Plan physical/die_plan/s81/plan_j8_hi4_r9.json, asbuilt physical/die_plan/s81/split_hi4x/asbuilt_vN.json (base ../../../.., clock_landing_table fixed). plan_gate_pre PASS.

## Running
- elab/strict bind --all-gaps/LATCHECK: intel2 unit oth-ubuntu-3180765-1795319395, script r9/bind_r9.sh, log r9/bind_r9c.otrun.log, gate logs r9/gate/, bind out treeJ8/physical/die_plan/s81/plan_of_record/native_bind/out_r9.

## Next
1. On bind green: kit specs already written (private-spec, intel2 r9/specs/<item>/spec.json, --bind-out out_r9, --src-manifest off): run `kit_wave.py run-item <spec>` for svc_hi_dsdv_svc_rs__t4 and __t4_att (place-only pair first; FABLE: one pair to confirm before anything else).
   Expect att GEN trouble Codex hit on J7 (epyc2 north/hi4_regen: exact macro names, 98-site fit memory = 8 staging 160x265 + 4 PMEM 256x256 SRAMs instead of ~601k soft bits, stage path aliases; scripts gen_att_fit_memory.py, correct_fit_macro_stage.py, finish_att_fit.sh) and rest clock landing x (epyc7 north/hi4_place_only/prepare_rest_clock_pin.py).
2. Then FABLE ranks 3-4: +2 stages on Y_p (1.86 mm endpoints), att macro-to-macro nets (eng _Y, load_s, rd_data 1.3-1.5 mm) need stations or macro re-order.
3. Hand hi4 rows to S81-J6-ASSEMBLY-R5 once a pair places clean (PLAN = plan_ftresite_r9 + hi4 split; FILE lines = split_hi4x dir, ovl_hi4 RTL, census_x_r9, ovl_j8).

## 11-21 22:xx update
- ADOPTED all s81 svc rows (COORD sweep 21:50): COORD-ROUTED-OWNERS.tsv rows 113-122 (incl s81 svc_*) -> OPUS-FIX-S81-SVC-R9. Choice posted: lo t2/t3/t4 + stale svc rows RELAUNCH ON J7 via the wave after 04:14 apply; watch launches, fix real failure classes.
- Bind fixes: main c6b360d4cd + 8ad54f25f4 (dead_inputs split-piece rule; installed in treeJ8). Die reset relays re-planned (relay_r9.sh -> relay/plan_relay.json, 2 rows: fW0_p1_b0, svc_13) and installed as plan_j8_hi4_r9.json (pre copy relay/plan_j8_hi4_r9.pre_relay.json). Full gate rerun: unit oth-ubuntu-2471689-1795324147, log r9/bind_r9f.otrun.log.

## Owned svc types (all, OWNERS-SWEEP token list)
svc_hi_dsdv_svc_pvso_entry__t1 svc_hi_dsdv_svc_pvso_entry__t1_rs svc_hi_dsdv_svc_pvso_entry__t2 svc_hi_dsdv_svc_pvso_entry__t2_rs svc_hi_dsdv_svc_rs__t1 svc_hi_dsdv_svc_rs__t1_rs svc_hi_dsdv_svc_rs__t2 svc_hi_dsdv_svc_rs__t2_att svc_hi_dsdv_svc_rs__t3 svc_hi_dsdv_svc_rs__t3_rs svc_hi_dsdv_svc_rs__t4 svc_hi_dsdv_svc_rs__t5 svc_hi_dsdv_svc_rs__t5_att svc_hi_dsdv_svc_rs__t6 svc_hi_dsdv_svc_rs__t6_rs svc_lo_dsdv_svc_rs__t1 svc_lo_dsdv_svc_rs__t2 svc_lo_dsdv_svc_rs__t3 svc_lo_dsdv_svc_rs__t4 svc_lo_dsdv_svc_rs__t5 svc_lo_dsdv_svc_rs__t6 svc_lo_dsdv_svc_rs__t7 svc_lo_dsdv_svc_rs_w__t1 svc_hi_dsdv_svc_rs__t4_att

## Codex 11-22 01:42–02:10 takeover

- Both inherited R8 kits are terminal at the stock HPWL guard before resize. Rest 1.319 and Att 1.316 versus 1.3. Viewed both actual 3_3 layouts. The R9 endpoint-ordered cut replaces that candidate at exact plan `755235acaa02`. Planned matching is 8,032 physical sites across ten paths including ten epochs, compared with 13,409 R8 payload and 8,022 R9 payload. Both R9 pieces have zero planned pin/tap blockers. Visual review coord `1c4305849e7`. No placement on the old cut.
- Current independent native replay is intel2 unit `oth-ubuntu-3600463-1795339558`, `bind_r9i.otrun.log`, exact plan/as-built `755235acaa02/f7b4bb9f3ad1`. Elaboration is green and reused. Prior `r9h` sole terminal issue was the cross-owner LEPe station sink. Current private plan omits the unmatched row. S81 composes its LEPe owner first and performs the coordinated die relay replan. The current emit tree remains intact.
- For exact internal kits after the R9 native gate, `prepare_hi4_r9.py TYPE OUT source` runs stock bind kit-rtl, reset and stations; `r9_fit_hi4_sources.py TYPE OUT` stages separate source and placement path corrections after native cone checks; `prepare_hi4_r9.py TYPE OUT kit OUT/plan_hi4_physical_paths.json` runs stock generation. The real R9 sidecar is `split_hi4x/eW_sidecar.json` at `e853b3360976` and the as-built manifest is `split_hi4x/asbuilt_vN.json`. The old private spec paths name J7 files. `normalize_r9_hi4_config.py` restores the reviewed flow values and preserves the existing placement guards. Use viewed exact kit geometry, then E7 place-only. The wave geom goal goes into a GRT probe.
- Independent R9/J8 guarded ops sent to S81. `j8_intake_guarded/j8_svc_fstart_and_clock_fieldops.json` at `6d8e70c8acf3` supplies 33 nonoverlapping FSTART and hi4 Rest clock ops. Preview `bc9c0595529e` passed stock pre-gate 0 findings, unit 376466. Three M7 x2.144→3.104 coordinates already exist in the landing declaration. Coordinate correction changes the selected reset input fingerprint, so integrate it before the final native bind.
- Approved seven-layout face scan identified two physical admissions to repair. North t2 Rest and vertical t5 Att required inherited row spacing propagation, 23 and 24 boxes +4.32 µm X. It clears 1,977 and 13,941 blocked planned pins and all taps. Pin windows and lane prices are preserved. Separate four-op packet `j8_intake_guarded/j8_svc_seven_entry_clearance_fieldops.json` at `338a505c6df6`; preview `0a3089870c6b` stock pre-gate PASS 0, unit 529562. Image viewed, coord `2efb01b173f`. No intake adoption or route.

## 11-22 03:xx (R9 after limit)
- GATE GREEN unit 3600463: bind 0 / LATCHECK 947 PASS on plan 755235acaa02 + asbuilt f7b4bb9f (rt ae9a5815f02c; LEPE bout row dropped privately). Rows posted to R5 (post 008a8c37) incl Codex guarded ops 6d8e70c8 / 338a505c and ft3 rows.
- svc 16 rows held to J8 by R5 (j7-svc-split-j8-1122).
- hi4 kits: hi4_kits.sh (Codex prepare_hi4_r9.py source -> r9_fit_hi4_sources.py -> prepare kit) waiting for intel2 scratch >=153 GB (floor 150), log hi4_kits2.otrun.log, out kits/<TYPE>/gen/<TYPE>. Then normalize_r9_hi4_config.py <R8 reviewed config.mk> <kit>, copy to epyc7 opus-fix-s81-svc-r9/hi4_pair/{rest,att}/<TYPE>, run_kit place-only, review_exact.sh, read HPWL.

## 11-22 17:3x (R9 after weekly limit)
- main d14cac8bd2: kit_rtl_post.d/s81_svc_hi4_att_fit.sh + tools/die_plan/s81_svc_hi4_att_fit.py (t4_att only, exact witnesses, fail-closed); in rt b84fd457f5e7+. Witness PASS on R9 bind netlist.
- treeJ8 (intel2) tools + physical/common_flow = rt b84 (old: R9/tools_ae9a_treeJ8, R9/common_flow_j7_treeJ8). Plans: plan_j8_hi4_r9_rest_paths.json (ebaec49a), _att_paths.json (4406e60f), combined plan_j8_hi4_r9c.json (0eb75a19).
- r9c bind (b84, 8 thr) OOM 216 GiB after 12.5 h. RUNNING bind-only retry 4 thr/200 GB: intel2 unit oth-ubuntu-560289-1795397828, script R9/bind_r9d.sh, log R9/bind_r9d.otrun.log, out treeJ8/.../native_bind/out_r9c. On PASS: private-spec rest+att --tree treeJ8 --plan plan_j8_hi4_r9c.json --bind-out out_r9c --src-manifest seal --host intel2 --rt b84fd457f5e7 --goal route.
- RUNNING att place-only (FABLE check) on Codex r9c att kit: epyc7 R9/hi4_pair_r9c_prior/att, GOAL=place, log place_r9c.otrun.log.
- Codex hi4_face_e7 (private face plan 8beb74b5) gen refused: port geometry attn__svc_5__svc_11 / svc_11__svc_5 plan face != src type face -> clearance ops must move both ends.
