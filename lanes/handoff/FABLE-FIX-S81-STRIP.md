# FABLE-FIX-S81-STRIP handoff (S81 strip leaf family, 75 types; started 2026-11-16 20:40 PST)

Owner of strip leaf closure end to end. Executor: S81-TYPES-R-STRIP (Opus). Bind: S81-DIE-R2 (C4). Read first: lanes/FABLE-PD-S81-STRIP.md.

## State
- Cause 2 (GPL) MEASURED: die-scale drift in the last Nesterov phase. t75, TD off, same 3_2 DB, exit overflow 0.25 vs 0.10:
  median movable cell moves 98 um, 61,962 / 125,066 > 100 um, 32,817 > 200 um; landing-ring logic leaves its FIRM flops by 150-300 um.
  Density 0.65 / 0.9, TD off, keep-resize 0 do not stop it (worker pilots 1.30-2.07 x). Exit 0.20 is on the knee (t47 1.26 x, t75 1.06 x).
  Exit 0.25: t75 TD off 1.026 x, DPL average 2.0 um / max 91.6 um; t75 TD on 1.017 x.
  Data: epyc7 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/{dump/ov25.txt,dump/ov10.txt,cmp.py,gpl/t75_td0ov25}.
- SETTING: sparse kits exit GPL at overflow 0.25 (OT_GPL_SPARSE_OVERFLOW, OT_GPL_GUARD rule 3 in face_flops.tcl; gen_phys emits 0.25 on S81).
  Branch claude/s81-strip-gpl-stable-1116 @39ef73a234f (on r430 588ce81), pushed, 24 tests pass locally. NOT gated, NOT READY-posted:
  waits for the CTS reads below. Clone: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/lane (patch script ../patch_ovf.py).
  Interim form for a kit: `override export GLOBAL_PLACEMENT_ARGS = -overflow 0.25`.
- Proof RUNNING (ot-run, TD on, -overflow 0.25, GPL -> resize -> DPL -> CTS -> x1.45 census):
  t47 intel1, t75 epyc7, dirs fable-fix-s81-strip/gpl/{t47,t75}_ov25, driver fable-fix-s81-strip/pilot2.sh,
  census out fable-fix-s81-strip/sta/<t>_ov25, logs intel2 ~/fable-fix-s81-strip/pilot_<t>_ov25.log.
  Compare with the 0.10 kits: t47 -3,956 ps / 15,893 paths, t75 -1,454 / 10,091 (x1.45 census).
- Form B: r432 approved (claude/s81-strip-vp-xr-1116 @1a183f5a920, XR + 16 dswp copies). C4 bind by S81-DIE-R2 not landed.
  Worker asked (post da748a3f) for the bank-end placement mechanism of the vpw + XR flops; not answered yet.
- COORD 21:40 (closure strategy lever 3): setting, form B and dswp copies must be in the D5 tree before r437 releases 29 leaf items;
  tell S81-TYPES-R2 the setting when the CTS reads land (provisional told, post 56392285). No leaf kit at overflow 0.10.
- Stopped: epyc8 unit oth-ubuntu-1637513-1794831534 (old-plan B6gE t72 kit of this lane name, 17 h in GRT extra iterations).

## Next
1. Read the t47 / t75 CTS censuses. If the ring / station classes are gone (only the 285-endpoint vpw class and VP driver left): run
   `ot-run ... tools/fleet/ot-gate-remote claude/s81-strip-gpl-stable-1116@<sha>` and post READY to COORD; tell S81-TYPES-R2.
   If t47 still shows ring logic > 50 um from its flops: PD review fix 4 (ring logic placed with the band).
2. Review the worker's bank-end mechanism; after the C4 bind regenerate t34 / t62 with form B + the setting, image review, GRT read.
3. t34 GRT read of form B decides the 9 far types (> 500 um: t65 t3 t10 t74 t38 t13 t42 t31 t34): under +42 ps -> VS move ~100 um
   toward the banks as a plan row (S81-DIE-R2), not a second stage on all 75.
4. Sign-off t34 / t62, export signed leaves to AGIdock /archive/opentallas-signed-1114 + rtx-pro, then waves over the other leaf types.

## CODEX takeover 22:18-22:44 PST
- Corrected pilots ov25td30 remain running (intel1 t47, epyc7 t75); noB route/CTS launched,39ef stillHELD. Source corrective patch_ovf2 already applied but uncommitted in E8 fable-fix-s81-strip/lane; waitCTS classification before committing/READY.
- New opt-in placement source claude/s81-strip-vpw-bank-1117@e1b62d6096a (existing wt_xr clone). Gen optin OT_S81_VPW_BANK=1 installs bank-endFF allocator and persists ONE existing standard clock tap group, deriving actual hierarchy (t34u_vp,t62u_lf1_u_vp). Addedcells/cycles0. Earlier51ad88e normalGREEN61/61; e1b normalgate running intel2 ~/fable-fix-s81-strip/gate_bank_e1b.log client694480.
- Geometry/DPL proof ONLY (original nonXR copiedDBs, no signoff claim): intel1 fable-fix-s81-strip/bank_t34_dpl placed317VPWFF FIRM,maxbankdistance11.328um,clk_t33 standard118.2um frombankcentroid,DPL0failures/check_placementPASS,maxneighbor1.2um. epyc7 bank_t62_dpl317FF,max13.488um,clk_t36 standard97.8um,DPL0failures/check_placementPASS,maxneighbor1.1um. LOOKED gap-cluster images PASS-COND. Both prove bank-end mechanism, not fullB timing. B adds907XRFF ->1224cohort,<1500tap budget,stillrequiresfreshbind/fullshape.
- t75 actualreach defect isolated390bits onft0station4->5,max442.8um. Simple43.2umshift FAILED545macro overlaps (E8 cong/t75_ft0_shift43.json). Initial south-onlyrepack superseded due narrowroutecorridor. Finalv2 E8 fable-fix-s81-cong/t75_ft0_repack_v2/{rows,report}.json,review.png; builder../repack_t75_v2.py:ONLYstation4(bit_sitesindex3,regsindex4),1105bitsinclpad,maxadjacent380.7um,0macro/otherFT hits,0FF/0cycles. Fullheight east-of-ve_s band399.6,4.32..418.284,54.0,≥2.16macroclearance; LOOKED PASS-COND. DeliveredDIE geometry,notadopted; generatedfixed/clock/PDN review pending.
- Originalt28/t34/t62/t72 stillGRTextraiterations,no5_1_grt.odb; preserveprogressing jobs. At22:37,t34iteration14/30,t28~6,t62~9,t72~5; rankonlywhenreloadedGRTexists.

## 00:55 PST 11-17 Fable resumed (decision post a546ed82)
- GPL setting of record: claude/s81-strip-gpl-td30-1117 @056783ac187 (r496, GREEN 94/94): sparse exit 0.25 + second TD pass at 0.30 + buffers kept below 0.35.
  x1.45 CTS census WNS / paths: t47 -3956 / 15,893 (0.10) -> -1538 / 1,486; t75 -1454 / 10,091 -> -531 / 867. 39ef73a alone and 78c5645 (-overflow 0.2 on all S81 kits) withdrawn.
  Pilot data: intel1 / epyc7 fable-fix-s81-strip/{gpl,sta}/<t>_ov25td30; drivers pilot5.sh (full chain), cls.py (class table).
- Left on t47 at kit RC (655 endpoints below -42): die reset 106 / -1096, die START 63 / -463, VP coefficient controls 202 / -264, vpw 281 / -249.
- Strip form for the pilot (decided): XR + 16 dswp copies (r432 1a183f5a920) + bank placement OT_S81_VPW_BANK=1 (r494 e1b62d6096a)
  + CFR with XR (r454 46684a7f11b) + lane reset copies (r495 d5946a58004). One form, t34 (3S=01000) and t62 (6N=00010) in C4.
- Asked of S81-DIE-R2 for C4: the two masks with CFR + reset copies, t75 ft0 station-4 repack v2, relay rows for die reset -> fstart
  and START origin -> reader start (hops within 405 um). Source HI_D stays 2 / GS 2 on XR leaves (stage_lfcs_netlist.leaf_depths trap);
  strip worker owes an XR-aware mapping branch with a test before the C4 ELAB.
- No qualified B physical kit exists: partial-context binds cannot emit (native_istations on omitted columns). Vehicle = fresh C4 full bind + LATCHECK.
- Inherited tapfix1 GRT kits still in extra iterations at 00:45 (t28 14/30, t34 27/30, t62 6/30 after NDR restarts, t72 12/30), no 5_1_grt.odb.
  Read with epyc7 fable-fix-s81-coltap/an/stage_sta.sh KIT OUT grt, rank with fable-fix-s81-strip/rank_strip.py, then stop by exact unit.

## Next (replaces the list above)
1. t34 GRT read (first to finish): class table at route RC; confirm vpw / VP driver / reset shares before C4 seals.
2. C4 lands -> generate t34 / t62 from the tree with 056783ac187, OT_S81_VPW_BANK=1; image review (XR + vpw cohort about 1,219 FF at the banks,
   one standard tap); run to GRT; read TT (gate -42) and internal FF hold; then route, sign-off, export to AGIdock /archive/opentallas-signed-1114 + rtx-pro.
3. t34 form B GRT margin decides the 9 far types (t65 t3 t10 t74 t38 t13 t42 t31 t34): below +42 -> VS move about 100 um as a plan row.
4. All 75 leaf types take XR in the following bind; waves of leaf kits after that. Hold s81-strip-gpl-d5 stays until then.

## 2026-11-17 10:1x PST strip-family ft re-slot (NEEDS-LANE 08:53, FABLE-CLOSURE-STRATEGY lever 5)
Work dir W = epyc10 /srv/opentallas-scratch2/claude/fable-fix-s81-strip; logs intel2 ~/fable-fix-s81-strip; clone W/lane7 (main 147b9727c1).
E = epyc10 /srv/opentallas-scratch2/claude/s81-b3-clk/rows/f2s5_S81-DIE-R (S81-DIE-R3). Floor = applied C4r3, plan 0126890b.

### Decided
- Re-slot, cores fixed: tools/die_plan/ft_channel_route.py (+ test_ft_channel_route.py, 5 tests), branch claude/s81-ft-channel-route-1117
  (local commit in W/lane7, NOT pushed, NOT gated yet). Each N/S slot is routed on the 4.32 lattice with every row gap, column gap and
  check channel charged once per slot (wires, not sites); bundles may cross M5-ceiling cores on 0.6 of M7; station count kept;
  bands only in channels the bundle runs through; --add gives +1 station when a route is too long.
- Moves-only VE rows withdrawn (COORD 09:2x). core_place --seed is not usable for single-core nudges: a vsw -12.96 seed on t57 moved
  VE_m / VE_s too (W/s57/event.json, 40 links over). No core move is needed in the result below.

### Measured (C4r3 plan, check ft_channel_tracks of main, W/cen.py)
- Base: 25 channels / 20 types over 0.70 (W/base/census.json); core_place --no-search base W/base/event.json (no new timing_over).
- --add, gate 0.70 (W/r9a/ledger.json): 20 of 20 types <= 0.70, worst 0.695 (t73), 19 types at 0 cycles, t67 ft9 +1 station (1 lane).
  t22 2.175 -> 0.457, t2 2.093 -> 0.566, t9 1.499 -> 0.65, t34 1.118 -> 0.52, t13 1.282 -> 0.641, t57 1.016 -> 0.618.
- --add --route-max 0.857 (= 0.60 of the tracks, W/r9ta/ledger.json): 20 of 20, worst 0.599, +11 lane cycles
  (t13 +3, t73 +4, t9 +2, t43 +1, t67 +1). Fallback if the region-mode capacity comes out under 45.6 / um.
- Without --add (W/r9): 18 of 20 (t57, t67 left).

### Running / next
1. W/cand.sh (ot-run, log ~/fable-fix-s81-strip/cand.log): full plan W/cand/plan_d7_strip.json, census, core_place score on the 20 types,
   G0 with main check.py (ft_channel_tracks blocking). Compare G0 errors with lanes/handoff/S81-C4R3-G0-BASELINE-1117.json (5).
2. If clean: `ot-run --mem 200 --priority plan --hosts epyc10 --dir W -- bash W/bind_d7strip.sh` (work tree
   kw45/src_s81_pin_3c913dbdfb23_d7strip_1117_work = C4r3 + this plan; strict bind, LATCHECK, G0, PRE). Then push the branch,
   `ot-run ... tools/fleet/ot-gate-remote claude/s81-ft-channel-route-1117@<sha>`, post READY + rows to S81-DIE-R3 for D7.
3. Calibration: asked S81-TYPES-R3 (post 53b299df) for t22 GRT on the C4r3 floor, OT_PG_TRACK_TRUTH_MODE=region, no early stop.
   No placed t22 / t2 kit exists. The result sets tracks/um for region mode; if under 45.6 use the 0.60 variant (r9ta form).
4. Not covered: the 5-6 inherited over-length core links per type (core_place base_violations) are as bound in C4r3.

## 2026-11-17 11:0x PST candidate built, bind running (replaces "Running / next" above)
- Branch claude/s81-ft-channel-route-1117 @02e762e464cb350c23a4c623e4fc8594701e307d PUSHED, gate GREEN 1/1 (main c9716823ec6,
  ~/merge-queue/gates/02e762e464cb350c23a4c623e4fc8594701e307d.json). READY not posted yet (waits for the bind).
- Candidate A (gate 0.70 at 45.6 tracks/um, --add): W/cand/plan_d7_strip.json sha c80a518b6299, rows W/cand/rows_d7_strip.json
  (31f6efed9e7a: ft_slots of 20 types, 90 slots; latency.lanes dn_s_7S_L3 stations 5 -> 6, cycles 13 -> 14 = t67 ft9 +1 station).
  Census (main check) 0 channels over, worst 0.695 (W/cand/census.json). core_place same flags as base (W/cand/event_same_flags.json):
  new timing_over 0; +1-register stations 9 and over-length links 66, both identical to C4r3 (inherited, internal stations / core links).
- Work tree epyc10 kw45/src_s81_pin_3c913dbdfb23_d7strip_1117_work (C4r3 c538c514 + this plan, manifest 1ed95f196850, link tree).
  G0 (tree check.py): 5 errors, identical to the C4r3 baseline (5 cuts rows), W/d7/g0/g0_report.json.
  Strict bind + LATCHECK + PRE + census: W/bind_d7strip_resume.sh, ot-run --priority plan, log ~/fable-fix-s81-strip/bind_d7strip_resume.log
  (first try failed only because the cached C4r3 elaboration was not staged; RTL is unchanged, so the resume copies asbuilt*.json in).
- Region-mode capacity: PG region mode cuts whole gcells of M5 (2 of 7.6 per 4.32 pitch) and M7 (2-3 of 15.2 per 8.64); from the strip
  pdn.tcl this gives about 41.9 usable vertical tracks/um against 45.6 (estimate, not measured). At --per-um 41.9 (W/r10_reg/ledger.json):
  24 types flagged (adds t10, t47, t74, t75), 22 fixed, +5 lane cycles (t73 +3, t9 +1, t67 +1), t75 and t8 not fixed. Not bound.
- Design target 0.60 at 45.6 (W/r9ta): 20 of 20, +11 lane cycles. Not bound.

### Next
1. Bind result: if strict bind 0 / LATCHECK PASS / PRE PASS -> post READY (branch + rows + tree) to COORD and S81-DIE-R3 for D7.
   If LATCHECK flags dn_s_7S_L3: drop --add for t67 (leaves t67 over 0.70) or pair the lane; report.
2. t22 calibration GRT (S81-TYPES-R3, asked twice, no answer by 11:00): decides 45.6 vs about 41.9; then re-run cand.sh with
   ARGS="--add --per-um <measured>" and re-bind. t75 / t8 need a look at that capacity.
3. First re-slotted kit to GRT: t22 or t34 (bundles crossing M5 cores on M7 are priced by the model, not yet shown by a GRT).

## 2026-11-17 11:3x PST READY posted
- D7-strip chain PASS: strict bind 0 / 395 / 873, LATCHECK 873/873, G0 5 = C4r3 baseline, PRE PASS, census 0 over (worst 0.695). READY post names branch 02e762e464c, rows cand/rows_d7_strip.json, work tree d7strip_1117_work (not published).
- Waiting on: S81-DIE-R3 to take the rows into D7; S81-TYPES-R3 t22 GRT calibration; then per-um from the measured table.

## 2026-11-17 11:5x PST r581 approved; waiting on t22
- COORD: region mode is NOT the default (DRT-0255 on H15): 45.6 stands, 41.9 case moot. S81-DIE-R3 takes the rows into D7; S81-TYPES-R3 launches t22 from D7.
- This lane: no kit build. Read the t22 GRT when S81-TYPES-R3 posts it (5_1_grt.log per-layer overflow, congestion.rpt over vsw / vq / rxsf and in the VE_s|vn_b 26-um gap). Over-core overflow -> lower OVER_USE (0.6 of M7) in ft_channel_route.py on a new branch, re-run cand.sh, re-bind. Else retire.

## 2026-11-17 22:5x PST RESUMED as strip-family owner (COORD; Fable limit reset; S81-FIX-OPUS covered 20:00-22:30)
- D7w APPLIED (manifest 263d6d57, plan 1698c515 = D6z + my D7 strip rows + t51 repoint); ft_channel 0 over. r663 face_guard advisory. r676 VPW / FT-snap pending S81 tools_refresh (FIX-S81-VPW owns t1 t7 t10 t31 t45 t53clb t74 t75).
- Wave state 22:14: 25 route rows RUNNING (plan 30c40fae, started 20:20-21:07); 17 re-slotted types in gen/place on D7w; 13 ROUTE-HELD on
  hold record s81-route-tree-01 (release tree_ready D7w; tree_check a8eb8838 ok 22:22 -> should enqueue by itself); t56 kit_rtl native-module
  error -> asked S81-DIE-R3; t32 pdn iostream = disk; t37 PLACE-HPWL 1.40 x OPEN.
- t37: GPL table min 5.66e6 um at overflow <= 0.5, 6.71e6 after the non-virtual TD pass (+78 % repair area), gate measure 7.83e6. Branch
  claude/s81-place-hpwl-baseline-1118 @4eeee568e39 is WITHDRAWN (premise wrong: real log still 1.38 x). Next = image of attempt_8 3_3 DB
  (epyc10 kw43-wave-1109n/runs/s81/kit-wave/s81/3fa87b84b18/items/ot_s81sl_leaf__t37/attempt_8).
- Lane clone W/lane7 is on branch claude/s81-place-hpwl-baseline-1118 (switch back before other work).
### Next
1. 23:00 tick: ROUTE-HELD count must drop from 13; else post tree_check evidence to WAVE-FLOW-R2.
2. First route results of the 25: read DRC, TT (gate -42), internal FF hold; class table per failure; sign-off + export AGIdock + rtx-pro.
3. Wave t22 (and t34): geom GRT then route GRT; over-core bundles on M7 -> OVER_USE if overflow.
4. t37 image, then decide (setting vs structure).

## 2026-11-17 23:5x PST HPWL gate READY; t25 first route FAIL
- READY claude/s81-place-hpwl-segments-1118 @1e569598d0c (gate 4/4): growth per netlist segment, repair step not counted, limit 1.3. kv_leaf t3 1.32 -> 1.286 PASS; t37 1.40 -> 1.36 STILL STOP (1.196 pre-repair x 1.133 post; buffers +3.1 pct). Asked S81-TYPES-R3 for ONE t37 attempt with item_env OT_GPL_HPWL_RATIO=1.5 to the CTS census (calibration of the 1.07-1.8 band). baseline-1118 @4eeee568 stays withdrawn.
- t25__cl431c660f route FAIL GRT-0116 (M6 568 + M8 347): 101 gcells all at x 360-480 y 0-7 (south face row), nets u_bin_leafdn_i0; epyc8 kw43-wave-1109n/runs/s81/kit-wave/s81/3fa87b84b18/items/ot_s81sl_leaf__t25__cl431c660f/attempt_5 (reports congestion.rpt). NEW family class: leafdn_i0 bin logic on the face pin row. Next: same read on the other 24 routing rows; find where gen places u_bin_leafdn_i0 (face_flops / bin placement) and move it off the pin row.
- ROUTE-HELD strip 13 -> 2. Lane clone back on claude/s81-ft-channel-route-1117.

## 2026-11-18 03:4x PST after the 00:30-03:10 stop
- r694 (HPWL segments) merged. 18 strip route verdicts: 12 SETUP_TRIAGE (-288..-733 est), 5 GRT (t25 t29 t35 t41 t68), t51 DPL-0033; 26 running.
- Route hold s81-route-tree-01 ON AGAIN: gen_hosts gained epyc10; tree_check a83afcd7/37cd6c46 bad (SHARED-INODE/DRIFT, hardlinks on the link-published D7w copy). 9 strip types held incl t22 (attempt 8 intel1, geom GRT no verdict). ALERT posted to S81-DIE-R3 / WAVE-FLOW-R2.
- t25 class measured: 595 leafdn_i0 input regs in 12 full rows y 4.32-7.29 on 598 pins / 124 um. PILOT: epyc8 /srv/opentallas-scratch2/claude/fable-fix-s81-strip/t25_ns2 (kit copy from floorplan, config.mk OT_FF_NS_ROW_STRIDE=2, resume.json start place, goal grt), log intel2 ~/fable-fix-s81-strip/t25_ns2.log. Read: 5_1_grt.log final table + congestion.rpt with W/cong.py (scratchpad copy; trivial to rewrite).
  GRT 0 -> plan rows budgets.face_flop_ns_types {type: {row_stride: 2}} for strip leaves with dense N/S bus windows (compute pins/um from plan) -> S81-DIE-R3; plus generator default. t29 is the landing-ring variant (u_cland_ft2_i, OT_CLAND_STRIP_DENS / cland_strip_rows).
- NEXT after pilot: endpoint class table of the 12 SETUP_TRIAGE types (t15: u_vsw/rst_n -297.8, tt_setup_repair RSZ-0074 crash; kit GRT wns only -17.6 vs gate est -350: find what the estimate adds).
- t37 calibration (item_env 1.5 set by S81-TYPES-R3 8c5db64e) never launched as of 03:08.

## 2026-11-18 04:5x PST gap + class table posted
- t15 gap closed: kit 5_global_route.rpt is the FF corner (last make is grt CORNER=BC); gate TT estimate is right. t27 same DB: TT+RC table -515, TT stock RC -397, FF gate -298, kit rpt -202.
- t27 class table (1,475 ep): VPW wdo_q 256/-515, VP write ctl 60/-494, VP driver/coef 1,008/-358, reset into 19 core rst pins (vsw -416) + 22 flops, istation/relay 78/-156. Tool: epyc10 W/gate_cls.tcl + gate_cls.sh, work W/t27sta.
- Asked S81-DIE-R3: XR on all leaves + cfr-with-xr + reset relay rows in the next event. NO strip relaunch before that tree. tt_setup_repair RSZ-0074 crash (t15/t16/t26) reported to WAVE-FLOW-R2.
- Open waits: t25_ns2 pilot (watcher), route hold tree_check (S81-DIE-R3/WAVE-FLOW-R2), t37 calibration launch (S81-TYPES-R3).

## 2026-11-18 05:2x PST t25_ns2 result
- GRT 0 with stride 2 (21 iters) vs 1,022; kit then DPL-0033 after GRT repair (place53892/place53728 overlap) = flow class, same as t51 -> WAVE-FLOW-R2.
- D8e row handed to S81-DIE-R3: budgets.face_flop_ns_types {ot_s81sl_leaf: {row_stride 2, inset_rows 0}}.
- Branch claude/s81-face-ns-dense-1118 @3bab6c734a3 (default-on rule) NOT gated: fires on 387/395 S81 types (all buses 4.6-4.8 pins/um). Asked COORD (a) leaf row only [rec] or (b) default-on. Lane clone is on that branch.

## 2026-11-18 05:5x PST ruling (a) done
- main @d4d7438dc78: FACE-NS-DENSE-1 opt-in (budgets.face_flop_ns_dense_pins_per_um, unset = off) + schema file; pushed with ot-push-main from W/lane7 (cone now tools + physical/common_flow + rtl). Old branch claude/s81-face-ns-dense-1118 @3bab6c734a3 (default-on) is superseded, do not merge.
- D8e row (S81-DIE-R3): budgets.face_flop_ns_types {ot_s81sl_leaf: {row_stride 2, inset_rows 0}}.
- NEXT on the first XR wave with the row in: (1) t29 GRT (u_cland_ft2_i ring at the south face, x 107-235 y 0-64, M5/M7): if still over, opt-in fix in the same form (cland_strip_density_types / cland_strip_rows_types for the leaf base name); (2) t25 vs t27: compare ot_face_flops.txt bank rows + congestion.rpt of both; (3) per-type class table with gate_cls.sh (needs 5_1_grt.odb kept); (4) t22 calibration; (5) t37 at ratio 1.5.

## 2026-11-18 06:1x PST interior congestion class
- t40: window x128-401 trapped under ln0/ln6/vn_b (34-43 um off S face), exit gap x290-334; t29 same class small. t25cl55: VP soft logic + SRAM pocket (x210-300,y390-450). t24/t68: no evidence left.
- core_place --window-clear / --slot-clear (W/wc1, wc2) REJECTED: rule binds moved cores only. RUNNING W/fc1 (--face-clear S:86.4:u_vn|u_vp.g_ln|u_ve --block-shift --take-regs on t40,t29; log ~/fable-fix-s81-strip/fc1.log, script W/wc.sh). Accept only if cores over the window >= 86.4 off face + timing_over 0; then private t40 kit to GRT (copy pattern of t25_ns2, needs gen from the new rows: ask S81-DIE-R3 for a gen or use gen.py phys in the D7w tree).
- phy__t1 / t29 handover from S81-COL-FLOW-1118: nothing on hub yet.
