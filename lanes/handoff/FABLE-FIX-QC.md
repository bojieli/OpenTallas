# FABLE-TYPE-REDUCE-S81-REST handoff (started 11-19 01:16 PST)

Scope: S81 families leaf, slice_station, serdes, dsdv_slice_c1x_C, svc_lo/hi_dsdv_svc_rs, kv_leaf (col families: FABLE-TYPE-REDUCE-S81-COL).
Lane dir: epyc9 /srv/opentallas-scratch2/claude/fable-type-reduce-s81-rest (a2..a12.py analysis scripts, census_*_v2.json, dedup_d8f.json, repo/ lane clone).

## State 11-19 01:5x PST: Step 0 done, no family passes, nothing running
- Posts: STEP0 01:2x (serdes PASS and leaf "faster" lines are WITHDRAWN) and RESULT 01:5x (final).
- Pushed: main f5f0d744f8, tools/precheck/type_census.py + 4 tests (bound RTL by plan module name; traffic_classes, landing_classes,
  estimate_no_reroute). No plan flag `type_template`, no generator change, no kit, no waiter.

## Why (measured on D8f plan_h2_2249.json, D8e bind RTL, registry 01:17)
- S81 types split on three position axes: (a) die traffic through the type as ft_slots (no streets; 73 of 75 leaves carry foreign lanes),
  (b) clock landing cohort (landing_contract + count-aligned strap set), (c) wrapper extras (rst_o export, sid parameter default, tap names).
- A pin template removes only window positions. Classes with windows re-slotted, no lane moved: leaf 65, slice_station 39, serdes 4,
  c1x_C 9, svc 13, kv_leaf 5. With the landing cohort: leaf 74, serdes 11, slice_station 46. S81 395 -> 274 (lower bound 51).
- schema.py ("bus is unbound ... tie-offs are not allowed") blocks a superset FT template until bind / landing / K-strap code supports it.
- Signed now: slice_station 35 of 46 (7 route, 4 pre-route); every other family here 0.
- serdes chain facts (for a later event): 4 shore chains; E-form types t2 t14 (0 FT), t1 x2 t16 (2 FT), t3 t15 x2 (4 FT), own bus on slot
  0 / 1 / 2 of the inner face, FT straight with 8 stations; S-form ends t4 t12 t13. A shift form (own bus on slot 1, W slot 1 -> E slot 0,
  W slot 0 -> E slot 2) keeps t12 / t13 and the slice_station pins, permutes the W slots of t4, and needs 9 stations on the 450 um jog.
- leaf floorplan check (a10.py): cores are 34 % of the leaf area; t69's core placement clears the FT station sites of 11 of 75 types, t27's 7.

## Open decision (COORD / owner), not started
S81 slice re-floor with street columns: leaf 75 + c1x_C 9 + kv_leaf 5 -> about 8 types + about 16 FT-only street types; street about 240 um
(0.6 track use), die x about +6 %, 35 signed slice_station types get new pins, one landing contract per template; 3 to 5 days before the
first template kit. Recommendation: decide at the first D8g leaf GRT TT read; start only if the FT-heavy leaves (t8 t72 t3 t75 t67) fail on
congestion classes after the common-logic fixes.

## Next for a successor
- Nothing is pending. If the re-floor is approved: rows = street column per slice half in gen_plan_v2.py, ft_channel_route with "no foreign
  FT in leaf", uniform landing contract for the leaf template, then one template kit to GRT TT (r712) before the bind.

## Re-verify after the census s81p_ fix (COORD 11-19, posted)
- col is bound as rtl/<type>.sv (0 s81p_col* files, 216 present); not affected.
- Per family: FT slots, buses, internal stations, taps = 1 variant each. Landing contracts differ per position in 10 of 12 families
  (h9_r2 7, h9_r1 4, p2 4, h10_r1 3, h10_r2 3, p3 3, others 2; p5 and p6 1); count_straps in 5 families; reset tree by position.
- 0 of 51 template groups mix landing contracts or FT slots. Speed verdict: 51 kits per event vs 216 (4.2x), every family faster.

## Code state (all on main 994caa6f8c05; off unless a plan sets type_template)
- tools/fleet/type_template.py: groups / check / flag / credit / records / rommap / view (+ tests). kit_wave: plan probe (PROBE_V 11),
  select() member skip, template_credit_step (every tick). col_inherit group=. Schema key type_template. tools/fleet/col_template_rows.sh.
- Push 083b4e3849 ran the whole touched test set green (the 2 enqueue_skip tests pass on current main).
- Automatic credit: a representative SIGNED on the current block -> records built on the die gen host -> hub
  ~/coord/autopilot/inherit_records/<die>/<member>__<block>/inherited.json + autopilot/inherit_members.tsv (the counter's file).
  With no image dir (die option type_template_rom_dir) the via map check is recorded as not done; it does not refuse the credit.
- rommap on D8e: 216 positions, 51 layouts, 9372 ROM images (35 ROM macros + 8 element cores per col_h9_r1 type), 0 errors
  (W/rommap_d8e.json). It is a map + check; the via-map-to-GDS writer itself still does not exist (rom_gen emits no GDS).

## Merge rows below 51 (plan level, measured on D8e df7446e48ba9; W/rows/d8e_tt = plan_tt.json 944ba058bbe2, sidecar_tt.json 60a304c234a7)
bash tools/fleet/col_template_rows.sh TREE BASE_PLAN SIDECAR OUT [--all-members]
- A reset keep-outs union (col_typemerge keepouts): 128 types get 326 more reset outs (max 4 per type), left open and declared. 51 -> 42.
- C collector superset, collector-form members only, --keep-taps (cland_col_superset): one landing contract per family, unused children tied.
  -> 25 plan layouts. Without --keep-taps the tap union gives 10 schema errors (added tap spacing, col_h9_r2 / p2), so taps stay per type.
- B one ring depth per sibling group and bus: 63 ports raised (depth 4 -> 8) on 29 r0 types; count_straps width follows at CA compose. -> 20.
- --all-members (plain tiles take the family contract too, R3b): 20 plan layouts, 15 after B. Costs landing pins/cells on 150+ plain tiles: not for D8h.
- Left after A+B+C: h9_r2 4, h9_r1 2, h10_r1 2, h10_r2 2, h10_r0_p1 2, p2 2 (two core placements), others 1.
- Schema validate of the result: 0 errors. NOT run: CA compose, bind, G0, LATCHECK, any kit. The bound-RTL key can only be counted after the
  bind; 20 is the plan-layout count and assumes the keep-outs union makes the reset trees equal (the only RTL difference found inside a layout
  today, plus one cland monitor in col_h10_r2 that the superset covers).
- Cost of the rows for closure: 0 cycles; more reset out pads and tied monitor pins on 128 / 78 types; deeper CA rings on 29 types (more slot flops).

## For S81-DIE-R3 (D8h)
1. Tree tools at main 994caa6f8c05 or later.
2. Rows: col_template_rows.sh TREE <D8g plan + trunk rows> <its landed sidecar> OUT  -> plan_tt.json + sidecar_tt.json; then the normal
   CA compose, strict bind, LATCHECK, G0 vs control. (Flag only, no merge: type_template.py flag BASE OUT "col_h*".)
3. After the bind: type_template.py check plan --bind-rtl <bind>/rtl --repo TREE  (expect 216 positions, 0 FAILED; groups = kits to build)
   and type_template.py rommap ... --out rommap.json (0 errors).
4. r712 proof kit: one representative of the largest group (col_h9_r1) to GRT TT.
5. Wave: 216 col rows become one per group; members show as skip "TYPE-TEMPLATE member"; credit is automatic.

## ROM via map to GDS at die assembly (main e1f0efbdd62d) - lane closed here
- The writer already existed (tools/mem_compiler/rom_viamap_gds.py, 8dfe82f36f: VIA1 21/0 overlay per unique image, merge by DEF);
  my earlier "no tool" line was wrong. Added: merge-map / verify-map (driven by type_template rommap, for one representative layout
  per group), rom_gen.py gds (one image, read back), all-zero image verify fix.
- Die assembly: type_template.py rommap ... --out R.json ; rom_viamap_gds.py merge-map --rommap R.json --macro <ROM datasheet json>
  --viamap-dir D --top TOP [--die-gds in.gds] --out out.gds ; verify-map the same with --die-gds out.gds (exit 1 on any difference).
- Check (no col layout is signed, so not against a signed layout): D8e map, frame u_f_0L01 at fW0_p1_b0/b1/b2 (col_h10_r0_p1, r1, r2
  templates, MX), 112 ROM macros, images = results/arch/s81_rate3_admission_1020/aproj_slice_frames/u_f_0L01/gold: merged 112,
  18 unique overlays, readback PASS 112/112. epyc9 W/gds/s81_0L01_via1.gds.
- Where images are: rom_gen personalise / rom_content.write_viamap write <INSTANCE>.viamap.hex. In the S81 tree only that 10-20
  slice-frame run has them (7 frames of 72, about 295 files each, named u_f_0L01_c1_5 for die instance u_f_0L01.u_r0.u_c1_5; the tool
  accepts both names). They are sparse test content (frame 0L01: 82 of 112 all zero, 120 vias). The release weight images for the 72
  frames are not in the tree: someone must export them before a real die merge.
- Open: (1) array origin inside the ROM macro is assumed (decoder width, 0) and the via sits at the cell centre: no base ROM layout
  exists to check it against; (2) the 8 element cores per type hold their ROMs inside the core layout: counted, not stamped;
  (3) no real die GDS was merged (overlay-only stream).

## 11-19 03:3x PST
- p1 (sle_ctl) in 4_1_cts at 03:19, no TT number yet; watcher alive. Wave: all 7 sle_ctl relaunched 01:19-01:56 on N4.3 / N4.3G (place).
- p2 was NOT a proof: st_b u_cland_origin is plan-sited (landing_placement.tcl rect from clock...origin_rect_um, landing_place.py 572-597);
  the hook kept it ("origins 1 sited 0 kept_firm 1"). p2 stopped 03:24 (run_p.sh pid 1032744, container d8e1a5d32291, watcher 1093956).
  The item_env on the two st_b wave items is a no-op for this class (harmless).
- Real fix = plan row: lanes/handoff/FABLE-FIX-QC-rows-stb-origin.json (origin_rect_um -> [219.96,786.26,237.24,803.54] for sle_st_b).
- p3 = same type as p2, landing_placement.tcl origin rect edited to that value (copy+mv before launch); started 03:25; watcher autopost.sh p3.
  Read: OT_CLAND / landing placement lines in 3_3, then CTS TT, then GRT TT end u_cland_rstart_tx/q (base -106.24 on the sibling).

## 11-19 03:5x PST
- st_b row file rewritten (v2, lanes/handoff/FABLE-FIX-QC-rows-stb-origin.json): 4 type groups measured. Origin move + 1 relay = 422-452 um hops (over 405); form A = origin unchanged + 2 relay stages at thirds (349-362 um, +2 cycles). No bind mechanism for extra relay stages yet (count_align_bind RELAY_STAGES const 2): NEXT = write it (per-region stage count + sites) if COORD picks form A.
- p3 keeps running as origin-only data point (rect at 220,786).

## 11-19 04:2x PST
- ON MAIN 45d943b418 RELAY-TX-STAGES: partition_types[origin type].landing_relay_tx_stages = n (count_align_bind relay_extra_from_plan via --plan-die, clock_landings u_cland_rstart_tx_p<i> chain, clock_landing_verify, schema + die_plan.schema.json). Tests: test_count_align_bind (+1), test_clock_landings (+1).
- Form A rows v3 handed to QC-PLAN-R3: lanes/handoff/FABLE-FIX-QC-rows-stb-origin.json (12 st_b types, key = 2, relay_sites for p0/p1 at thirds, hops 349-362 um). NOT bound by me. After the N4.5 bind: private kit sle_st_b_v2__cl14c98df5__pvcd986c42 to GRT TT.
- p3 = origin-only data point, still running; p1 sle_ctl waits for CTS TT.

## 11-19 SONNET-FIX-QC (successor; Fable limit)
- r713 FIX ON MAIN 5f65ed8017: clock_landings _tx_raw(at=, limit=): each RELAY-TX stage u_cland_rstart_tx_p<i> takes its raw reset from the raw copy nearest ITS relay_sites entry (reach 405 um; midpoint ot_dp_rrelay u_cland_rst_tx_p<i> beyond). No site = old tx raw. Test added; test_clock_landings + test_count_align_bind green.
- rows-stb-origin.json v4: no row change (relay_sites already carry stage positions); policy + checks recorded. All 12 st_b types: p0/p1 sites clear of every hard core (halo+2 um) on plan_n45_b.json b27995d3. Told QC-PLAN-R3.
- p1 sle_ctl (CTS, base -97.91) and p3 (origin-only, route) both still running on intel2 (run_p.sh p1/p3, autopost watchers 578596 / 519870 alive). NEXT: read p1 CTS TT, p3 CTS/GRT TT; after N4.5 bind, private kit sle_st_b_v2__cl14c98df5__pvcd986c42 (form A) to GRT TT.
- Lane clone: intel2 /srv/opentallas-scratch2/claude/sonnet-fix-qc-repo
- COORD 11-19: st_b form A rows go into N4.6 (not N4.5); the form A kit waits for the N4.6 bind. Keep p1/p3 watchers, post CTS TT when they land.
- COORD N4.6a fix: rebuilt sidecar by patching N4.5d table with relay_extra(plan_n46_a): epyc9 qc-plan-r3-n41p/n46/sidecar_n46c.json (+sidecar_relay_extra_patch.py); 12 regions stages 4, 36 K re-referenced; not yet bound. fable-die-qc-r (scratch3) dir is gone; asked FLEET-OPS-R.
- LEVER 6 11-19: sle_st_a_v2 loss = detour on 3 b_tw_data_i nets (+60 fF), cbf_q00_s2 = no station on x_0_1 b_d -> bc_o01 (28-buffer chain); posted. coll_ftc next.
- LEVER 6 11-19: GR-RC 2nd repair pass does not close (-37.52 -> -37.52), no flow change pushed; bc_o01 station rows FABLE-FIX-QC-rows-stations-n46d.json for QC-PLAN-R3 N4.6d; coll_ftc DBs found on intel1 ot-jobs.
- LEVER 6 11-19: bc_o01 row withdrawn (QC-PLAN-R3 plan sites); tap_d row FABLE-FIX-QC-rows-stations-tapd-n46d.json; b_tw_data_i detours = congestion (same-bus + ft ctl buses); coll_ftc = ring half-cycle ends, ~12 ps CTS->GRT.
- LEVER 6 11-19: CLAND-RING-GROUP opt-in on main d1ee896057 (row-wrap split of ring bit groups, coll_ftc tl_st_wi_i); proof (regen coll_ftc with OT_CLAND_GROUP_ROW=1, span + GRT TT) pending.
- 11-19: ring-group v2 on main 822e8ca0f1 (dry-place group); grp2 kit running epyc8/10 (spill possible), ring_pid_grp2; v1 had broken test_landing_column_fill (fixed in v2). RSZ-0074 on net87045: read pending after grp2.
- 11-19 14:20: 7 DEAD-OWNER QC rows owned by SONNET-FIX-QC; all alive (st_b_v1 pv38472fb8 old-plan N4 route job f8916312e802 live, left alone); heartbeat ~/sfq-l6/hb.sh every 2 h.
- 17:50: ring-group v2 proof failed (spans 359, GRT RSZ-0060), opt-in stays off; 7 QC rows all running, none failed.
- 18:15 5 failed rows: sc_v1 cl4590432d re-enqueued (4b00aa7c9228), cl5e017c6f pending ORPHAN flip; cbn_q11 x2 stretch gate advisory (main becd71085d) + wave retry; slw_su_c vmr LEF OBS blocks interior M5 pins (DRT-0073) needs decision.
- 18:45 vmr DRT-0073: lef_overrides on main d2c3111be0 (exact M6 from signed ODB, 5 pins access ok); relaunch of 3 su_c types waits for the N4.6e tools snapshot (QC-PLAN-R3).
- 18:50 vmr proof kit running epyc10 sonnet-fix-qc-vmrproof (pid file ~/sfq-l6/vmrproof.pid); retry rows pending QC-PLAN-R3 N46P confirm.
- 19:15 6 failed rows: cbn_q11 x2 private in place epyc7 (STRETCH_STOP=0), slw_su_c cl19bb38ef private vmrproof2 epyc10, st_a_v2 + tt_ctlm re-enqueued (orphans), st_a_v2 rebind needs N46Q.
- 20:05 tt_ctlm: no relaunch (Fable stop list); ad4d52b9ea00 already ORPHAN, nothing to cancel.
- 19:55 vmr proofs: cl92142dac in CTS, cl19bb38ef in 3_4; retry rows wait for N46Q live tree path.
- 20:50 su_l0: route B (contract files) works for l0 only and breaks 6 siblings (tap 392.5 vs signed means); reverted (.SONNET-DISABLED-1120); plan rows for N46T.
- 21:15 su-lane family rows + contracts + enable script in lanes/handoff/FABLE-FIX-QC-su-family/ for N46T; 7 types check pass.
- 21:40 slw_su_l1 legacy = 6 cland taps owner Measured..., cland signoff lacks fclk per-pin mean; proposal: extract fclk from signed exports, contracts+rows next event.
- 21:55 cland per-pin means extracted on rtx-pro (validated vs signoff clk <0.06 ps), contracts in lanes/handoff/FABLE-FIX-QC-cland-means/ not installed; ship with su_l1 rows next event.
