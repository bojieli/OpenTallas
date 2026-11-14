# DIE-QC-100 lane handoff (QC = qwen_compute die owner)  -- updated 2026-11-12 15:55 PST

## 1 Scope
Finish QC s28 compose as ONE event: s28a + s28 items (B,C,D,E,F,W) + HF-1c delta (claude/qc-s28-floorplan-1112@ea7be452d3, APPROVED w/ GEOM-VIS-3 conditions a/b/c) + REACH-FIX taps; G0 + strict bind; READY with sha + drawings. Types go to P&R only after a GEOM-VIS-5 verdict. Hourly STATE on lanes/COORD-REVIEW-QUEUE.md. QC: 2/120 types, 31/31 cores signed off.

## 2 Worktree / dirs
- Compose work dir: epyc9 /srv/opentallas-scratch2/claude/qc-s28-hf1c (dead HF-1c lane's scripts: apply_hf1c.py, compose_hf1c.py, stations_hf1c.py, taptable_hf1c.py, gates.sh, g0diff100.py (mine)).
- Plan-tool tree: epyc9 /srv/opentallas-scratch2/claude/wt/qc-s28-hf1c (HEAD ebaf94d011 = main merge; UNCOMMITTED: plan_of_record/zz_*.json intermediates, sink_bins/hf1c/, street_rule_bins, glue bins -- intermediates, do not commit as-is).
- FROZEN compose base: qc-s28-hf1c/base_s/plan_hf1c_s.json sha 55d318eece08 + base_s/side_hf1c_s.json 4134fed37bce (= s28a+B+C -> apply_hf1c -> compose taps -> reattach -> D(hf1c) -> E -> stations). Ref pre-HF-1c plan zz_s28a_bc.json (G0 268). base_s G0 611 -> 381 NEW (START tree 244, monitor edges 88, latency 38, geometry 9, faces 2). Report out/hf1c_s/g0/g0_report.json.
- My scratch (localhost): /tmp/claude-1000/-home-ubuntu-OpenTallas/c228d9e1-f423-4eaf-829b-3bad2a9c2331/scratchpad (qc100_post.sh = queue poster, stop.txt, stopped*.log, hf1c_types.txt).

## 3 Running jobs (mine)
- Sub-lanes (Claude background agents; each writes its own dir + hourly STATE as its lane name):
  - QC-S28-HF1C-LAND: epyc9 qc-s28-hf1c/land/  (START provider re-site 215 rows, cland_mon pins, latency explain, geometry, faces)
  - QC-S28-TAPS: qc-s28-hf1c/taps/  (fold F 833026c823 + west-strip W family qc-s28w/apply_s28w.py + cbn_q00__cldbcda913 start-copy depth bind fix + GEOM-VIS-3 tap table / N-S split; REACH-FIX-2 tool not ready -> repo density recipe)
  - QC-S28-ROUTE: qc-s28-hf1c/route/, wt/qc-s28-route (R1/R2 variants vs 6 pins/um face rule; cbx condition c: C on _h types + bc leg relay sites with ft:a22)
  - QC-S28-VISFORM: qc-s28-hf1c/visform/ (delta_visform.json 5b7727e98ab6 -> plan e296334570cb at 06:42; sc E channel, fw/st_a E face, sle_stm_v1, ctl ring form; sle_ctl__cl372cea1c override gen fail = GEN-CLASS-1)
  If a sub-lane is dead: read its dir handoff/README and its last STATE line; deliverable = guarded delta on base 55d318eece08.
- No P&R builds of mine running.

## 4 Watchers
None besides the sub-lanes. Queue post: append line to ~/coord/lanes/COORD-REVIEW-QUEUE.md then coord-commit.sh.

## 5 Results not yet posted
- R1/R2 seam numbers (dead lane r1r2/out/seam_budget.txt): stm|ctl 613 um 3378 pins (5.51/um); +R1 7.25/um, +R2 6.25, +R1+R2 8.00; fw|st_a +R1 6.91. R1 as drawn fails the 6/um face rule -> ROUTE lane picks the variant.


## 5b Sub-lane results (07:45)
- ROUTE DONE: route/delta_route.json e118ba855dc3 (apply_route.py), plan f9689987b7d6, G0 0 new. R1/R2 = variant (a) none (all variants fail 6/um faces; e1 = COORD decision, default not taken). cbx: C station ok on _h; 11,342 relay_sites/type max 401.8 um; ft:a22 in-window. Branch claude/qc-s28-route-1112@6997b0a97f local epyc9 wt/qc-s28-route.
- TAPS DONE: taps/delta_taps.json + compose_taps.py (apply, CONFLICT exit 3) -> plan 67b0bf06d8dc side 3935c9347e09; G0 611=611. F re-derived on HF-1c su; W family 9 types density cap 1200; reset relay re-pick on 81 types; 4 trees +1 reset depth (coll_s, coll_ft__cl78c7b300, coll_ftn, cbn_q00__cldbcda913), eq_rows.tsv. STRICT BIND base 47 err -> 32: 30 R8_STALE (r8_sw2 predates HF-1c stations: REGEN NEEDED), slw_hc3__cld86a7ad4 reset (no depth-2 relay for a START stage), cbx_q10__cl89936551_h ID strap mismatch. Reset reach: 177 START-stage + 117 local-copy refs > 405 (base 97/2) -> reset-tree fix needed.
- VISFORM DONE: visform/delta_main.json 16527d362634 (fw/st_a/st_b face_flop_ew_types, sle_ctl ring key, 24 stale overrides dropped) -> plan 05cb29a2ffd3 G0 0 new; delta_sc_echan.json 6add77fabc2f on top -> b41760698828 (+33 G0 hop errors -> run stations_hf1c.py after compose). Branch claude/qc-s28-visform-1112@72ddbf5bad local epyc9 (face_flops.tcl/gen_phys/schema change, must merge with the event). NOTE main taps.py lacks `from pathlib import Path` (81f2a99558) -> G0 NameError on plans with sink bins; told ROOT-MERGE.
- LAND: running (land/).


## 5c Compose (08:35) -- epyc9 tree wt/qc-s28-hf1c plan_of_record, scripts qc-s28-hf1c/compose/
- run_c.sh: zz_c0_base 55d318eece08 -> zz_c1_taps 67b0bf06d8dc (side compose/side_c1.json 3935c9347e09) -> zz_c2_route 41eaaaa2502d -> zz_c3_vfm 7efc0a79318c -> zz_c4_vfsc 16ca44611ab4
- stations_hf1c.py -> zz_c5_st e7fb79028919 (rep compose/rep_st5.json, cycles compose/cycles_c5.tsv; 6 pin-to-pin hops remain -> VISFORM delta_sc_fix.json on zz_c5_st)
- compose/fixup_qc100.py -> zz_c6_fix cd947c08b90a (F1 grid snap 129 cores/33 types; F2 st_a r2.u_sks x 354.24; F3 slw_st_b lec_hints). Gates running: qc-s28-hf1c/out/c6 (compare with g0diff100.py vs out/s28a_bc/g0/g0_report.json).
- Pending deltas onto the chain: VISFORM delta_sc_fix (on zz_c5_st -> re-run fixup), LAND (land/; rebase on final chain).
- QC-S28-BIND sub-lane (bind/, wt/qc-s28-event branch claude/qc-s28-event-1112): real event tree + r8 regen + cbx_h straps + slw_hc3 reset + reset reach + strict bind.
- QC-CLASS-TRIAGE DONE (qc-class-triage/): LEC st_b = missing replica hints (F3 fixes slw); slw_hc3__cld86a7ad4 LEC 85 pts unknown -> KW-FIX-46; macro_channels -> F2; landing band OK on HF-1c.


## 5d Compose (09:00) -- tool tree for gates = qc-s28-hf1c/visform/gtree (schema needs VISFORM tool files); run compose/gates_g.sh
- zz_c5_st e7fb79028919 -> VISFORM delta_sc_fix f09979e10115 -> zz_c5b_scfix 47aa44ee2f52 -> fixup_qc100 -> zz_c6b_fix -> compose/snap_lattice.py (cluster-aware floor/ceil, cl_* landing views exempt) -> zz_c7b_lat 3d1f6c30cec4
- gates out/c7b: schema 0; G0 611 (= c6b, 0 NEW); G0C 1448 -> 762 (686 hard_cores gone, 0 net new). vs s28a_bc: G0 NEW 385 = LAND classes (332 START/monitor, 42 latency=42 gone, 9 geom, 2 faces)
- Residual HF-1c-origin G0C (cl_ landing views 38, u_t ck M5 x 10, su_l0 internal_stations 3, core_faces 31) -> sub-lane QC-S28-RESID (qc-s28-hf1c/resid/)
- Final chain order: c6b + LAND delta + RESID script -> snap_lattice (last) -> gates -> BIND (QC-S28-BIND, bind/) -> bus_groups/EQ/tap table/render -> READY


## 5e 13:00 (after usage limit; COORD 12:4x orders)
- ROUTES (COORD (1)): 7 GEOM-VIS-8 ISSUES-ACCEPT rows ENQUEUED 12:53 via intel2 /tmp/qc100_route_release.py (wave enqueue_pass under kit_wave.lock). Blocker was die-wide QC hold_items '*' (KW-FIX-46) skipping retry_enqueue + st_a family verdict line not parseable -> 6 per-row transcription lines in GEOM-REVIEW.md. '*' hold left in place. FIRM GRT WATCH sle_st_a_v2 + slw_st_a_v2__cl9f076a5c (E column > 0.9 -> stop).
- sle_ctl 547k > 400k cap (COORD (2)): sub-lane QC-S28-CTLCAP (qc-s28-hf1c/ctlcap/): breakdown first, then split/re-form in s28.
- Chain: ... zz_c7b_lat 3d1f6c30cec4 -> resid/resid_fix.py (+ sidecar resid/side_resid.json b41986f8d639) -> zz_c8_resid 0f0dbf06115f (G0 611, G0C 711). Final order: c8 + LAND delta -> snap_lattice -> resid_fix -> gates -> BIND scripts.
- LAND died at limit (last 16:42 UTC, face pack worst 69 > 64); resumed on c8 (part 1 START/mon/geom, part 2 faces).
- BIND at event tree fa7cad9b3a (wt/qc-s28-event); scripts bind/bind_fix.sh (r8 derive, fix_h_straps, reset_pad, reach_fix class 5).
- 'other flow error' owner table re-posted 12:58 (with triage).


## 5f 15:55 -- chain + bind status
- FIRST CLEAN STRICT BIND: zz_c8_resid 0f0dbf06115f -> chain c8t -> plan_final 7ea8c9c61c2a, BIND_RC=0, bus_groups f5c931ea8494, r8 7f56f61bfc8d. Event tree epyc9 wt/qc-s28-event 0e7f05581b -> 3b3a3de8ff (+ist-pad), local.
- READYs posted: claude/qc-coll-clock-merge-1112@7181d90f66 (bind clock_merge); claude/qc-bind-ist-pad-1112@4b6dee512d57 (lane_pad source-station double count, opt-in kit_source_station_pricing). Pending: QC-COLL-HOLD clock_contract d2d related branch.
- Chain order (final): c8_resid -> ctlcap_kp 2fb778fc4fa5 (+ .kit_pricing.json) -> collmerge on kp (+ .clock_merge.json incl glue d2d) -> glue d2d merge -> LAND delta -> forwarded-hop fixes (RESID) -> snap_lattice -> resid_fix -> gates -> bind_fix.sh chain (straps/pad/repick/local_copy_fix/tap_ident/cm_inject/kp_inject) -> bus_groups/EQ/tap table/render -> READY.
- Sub-lanes: QC-S28-BIND (bind/), QC-S28-CTLCAP (ctlcap/, done), QC-COLL-HOLD (collhold/: coll merge c8b, d2d merge, census done), QC-S28-RESID (resid/: forwarded hops), QC-S28-HF1C-LAND (land/: part 1 START/mon/geom, part 2 faces).
- Routes: 6 st_a running on epyc4 since 12:58 (GRT watch sle_st_a_v2, cl9f076a5c); coll_s a2 FAIL post-CTS hold -268.69 (root cause = 3 CTS trees, fixed in event, not relaunched on hcut1111).
- Cross-die notices: CLOCK-SPLIT census (only QC coll + glue d2d); ist double-pad today: KV 120 lanes, HBM 10, S81 58 (owners decide).

## 6 NEXT STEPS
1. Collect the 4 sub-lane deltas (each guarded on 55d318eece08). Compose order: LAND -> TAPS -> ROUTE -> VISFORM (each apply script refuses on from-value conflict; resolve by hand, keep both intents).
2. gates.sh on the composed plan (in tree plan_of_record); g0diff100.py vs out/s28a_bc/g0/g0_report.json: rule = 0 NEW errors (or each remainder explained + COORD ruling).
3. Strict bind on composed plan (recipe: qc-s28w/gates_s28w.sh + bind_s28_w.log; bind-strict-src; BIND_RC=0, 0 unbound/undriven), bus_groups, EQ with declared cycles (cycle tables: planq/cycles_hf1c.tsv + sub-lane tables) -> TOK-VERIFY.
4. Render whole die (QC-S28-DIEVIEW after.sh) + tap table (cond b); view them; commit package on branch claude/qc-s28-event-1112 (plan gz, deltas, apply scripts, reports, drawings) and post READY [DIE-QC-100 -> COORD, ROOT-MERGE-60, KW-FIX-46, GEOM-VIS-5] with sha + drawings.
5. After READY: lift kit_wave.json hold_items "WAIT-FORM HF-1c" entries ONLY when the wave repoints to the s28 plan; types place, stop at WAIT-VISUAL, route only after GEOM-VIS-5 verdict.

## 7 Open READY/ASK
- None open by me. COORD asked (06:2x) to stop old-floor HF-1c builds: DONE (RESULT posted). KW-FIX-46: reap stopped rows as CANCELLED not FAIL.

## 8 Gotchas
- WAIT-FORM is implemented as dies.qwen_compute.hold_items in ~/coord/autopilot/kit_wave.json (coord 858d6f83f53, backup kit_wave.json.bak-dieqc100-hf1c); edit under flock kit_wave.lock. Live wave code: intel2 /srv/opentallas-scratch2/claude/kw38/rt/tools/autopilot/kit_wave.py.
- HF-1c type set = 76 types (hf1c_types.txt); st_a/st_b/ctl are moved-only (block unchanged) and were left running.
- epyc9 load ~80; gates take 10-15 min. Plan must sit in the tree's plan_of_record for relative pins_file paths.
- QC-S28-C 93ffbd113a23 is HELD (cond c) -- do not merge it standalone.

## 5g. 16:40 refresh
- Chain head: plan_of_record/zz_collmerge_kp_d2d.json b00e9e804767, sidecar collhold/side_zz_collmerge_kp_d2d.json e292ebb838c1, siblings .clock_merge.json (coll_n/coll_s {coll,serdes:core}, coll_ucie {coll:core}, glue {d2d:core}), .kit_pricing.json eb38cf8a8c92 and .bind_requirements.json. G0 415 / G0C 515, 0 new vs ctlcap/g_kp.
- Glue sink bins are a PROXY (no glue place exists); re-dump at the first s28 glue 3_place.
- READYs posted: 7181d90f66 (bind clock_merge), 4b6dee512d57 (ist pad, opt-in), 6a2b2c7e2d3 (clock_contract d2d related, 16:30).
- ist audit confirmed by CTLCAP reconcile (ctlcap/ist_reconcile.py, reconcile_c8t_kp.tsv): 144/144 cb pad drops, diff 0; figures QC 144, KV 120, HBM 10, S81 58. Stale-RTL types under kp: cb q00/q11 receivers, hc1, st_a v1/v2, 4 ctl. CTLCAP is writing ctlcap/stale_types_kp.tsv.
- In flight: COLL-HOLD on the 5 hops over 405 (coll_n flt_o 472, fltv_o 470, rec_rx_s0 645; glue tt_pw 440, visibility_slot 449), stage L made a hard fail. CTLCAP on W5 PARAM_REGEN. RESID on 8 forwarded hops. BIND on the cm proof against the d2d head, merging 6a2b2c7e2d3 into wt/qc-s28-event by hand.
- Next: LAND parts 1-2 on the final head -> snap_lattice -> resid_fix -> gates -> bind_fix.sh chain -> bus_groups, EQ, tap table (HF-1c cond b), die render -> event READY.

## 5h. 17:0x
- Chain head: zz_collmerge_kp_d2d_l405 dc9717d67087 (sidecar e292ebb838c1). No landing hop over 405 in coll_s/coll_n/coll_ucie/glue; max 403.2 (glue). 7 pins re-sourced to the nearest same-family tap, 0 cycles. Gates 0 new. The hard rule is in collhold/land_fix.py and coll_merge_apply stage L.
- Re-source skew: fits at contract level (same tap group, insertion 250±40, kit window 30 ps, collhold/diag_ringmargin.py). WATCH: the ring-hold / clock-landing verify in the first s28 kits of coll_s, coll_n and glue confirms the built number.
- Double-pad: the 15:1x withdrawal STANDS (COORD). CTLCAP is measuring one named lane per die: (a) stages, (b) table, (c) schedule consumer, delta, functional vs perf. I post one RESULT when it reports. W5 is paused until then.
- d2d-related 6a2b2c7e2d3: COORD approved for merge.

## 5i. 2026-11-12 15:49 PST (real clock; section stamps 16:xx-17:xx above were about 2 h fast)
- Final event head: zz_collmerge_kprv_d2d_l405 eb9b70cf799c. Base kprv 705a1e9fe0b5 (W5 rv-pad: sl_W*_st_a__x_st_a_fe at 19), sidecar e292ebb838c1, siblings clock_merge f6219a3387b4, bind_requirements fcc229977deb, kit_pricing eb38cf8a8c92 (a flag file). Gates 0 new vs ctlcap/g_kprv. Priced lanes 379, ids same as kp.
- COORD ruling: QC binds with kit_source_station_pricing ON from s28. No c8t-era-or-older cb/hc1/st_a/ctl kit counts. No signed QC item carries an affected cb lane. The QC token sim runs on bind-only RTL and cannot see kit u_ist, so as-built lane_proof is now a chain step in BIND.
- BIND lane_proof on kp2_g1: 3 real mismatches on sle_fw_v3 receive-side u_ist (sl_E4_fe cmd/dr, sl_E5_ctl x_ctl_fw_p1) -> CTLCAP. 6 su types fail kit_istations rc 1 (a KIT BLOCKER: su_l0 x_su_c_p1_o width 450 vs face 369; slw_su_l1 cland port) -> CTLCAP. Landing to be measured via strap_k K+1 vs table. 21 hard-PHY lanes OK_HARD.
- coll_n collector +1 cycle (depth 3 -> 4) is level-sensitive at the consumer (qkd_program_commit.sv:78,123, no counter), so it is harmless. Stale estimate: sidecar boot_budget.local_registered_depths.coll_n = 5 is not recomputed (ready_at_glue estimate 1256, at most 1257). Not a gate; regenerate at the next clock_landing_plan run.
- Watch: glue sys_face tt_fab/tt_kok/tt_kwd hops 400.2/401.8/403.2 um on clk_t42 (2-5 um margin). Ring-hold verify on the first s28 kits of coll_s/coll_n/glue.
- 6 st_a hcut1111 routes on epyc4: old-plan; KW-FIX-46 asked to stop them by exact container.
- Waiting on: BIND final chain on the head, CTLCAP (fw_v3 + su), RESID 8 forwarded hops, then a re-run, tap table, render, event READY.

## 6 CURRENT STATE 2026-11-13 09:02 PST (supersedes sections 5x where they differ)
Rulings in force: QC binds with kit_source_station_pricing ON; lane latency / reset eq rows never baselinable; the wave switches to s29 at 11-15 04:00 (s28 = base, not adopted); decision B (single-region die H-tree) WITHDRAWN 11-13: QC moves to regional clocks with landed crossings, and HOLD-TAP-1 delivers the region-form delta for s29. No more s28 die-clock proofs.
s28 (epyc9 wt/qc-s28-event2, branch claude/qc-s28-event-1113 local; HEAD 5aac3f7883 = fb09d8d626 merge of SU fix 3df9d1b1e0 + reset_steps.sh):
- SU double insertion fix 3df9d1b1e0 is MERGED to main (train 51, c326df3f3f).
- QC-S28-BIND re-runs the chain as tag ev3st (plan 736058c458ee): targets LANE_ASBUILT 0, r8 derive, g2 BIND_RC 0, W5 closed, lane_proof 0 mismatches and 0 UNMEASURED. ev2st ended BIND_RC=1 (pre-fix). I post the READY.
- Known s28-head defects, all fixed in s29: coll_core tap_radius 600 (gen refuses; at 400 the bind refuses sink (2.0,91.04)) -> COLL-HOLD; 18 types / 205 off-row ft bit sites (GPL refuses) -> QC-FTGRID-1 (plus a die-agnostic G0 grid check, branch claude/ft-site-grid-check-1113); sle_fw_v3 knee 4 chains > 403 -> FWV3-KNEE-1 delta qc-proof-1/fwv3 (5fae9c56473e, +1 cycle on 4 lanes); 11 cland masters lack landing_evidence (cbn_q00 x2, slw_su_l1 x2 kits read deleted host files) -> QC-PROOF-1 branch claude/qc-cland-evidence-1113.
- s28f = head + ftgrid + coll_core (+ reset_steps.sh): I compose it and post its sha for HARD-QC-FORMS-1 / QC-FORMS-2 to rebase on.
s29 order (COLL-HOLD s29_final.sh, epyc9 qc-s29-reach): CTLCAP head (s29a: ctl V3 split with u_ctl + u_tap HARD, FIRM stations on 7 buses per type, about +8 cycles per type, ledger pending; projected 360-376k under the 400k cap; s29c u_ctl-soft was gate-clean but over cap) -> hand delta (su_c tap, coll_core tap, coll_n monitor re-site) -> fw_v3 knee -> REGION FORM (HOLD-TAP-1) -> R-REACH-1/4 -> START/monitor relays (trunk sites must come from the plan's current clock tree; relay flops must be emitted AT the relay site, proof requested) -> reset_steps.sh -> strict bind chain -> READY before 11-15 04:00.
Reusable reset step for form lanes: RF=1 bash epyc9:/srv/opentallas-scratch2/claude/qc-s28-hf1c/bind/reset_steps.sh IN OUT TAG (straps, pad vs s28a_bc AND vs the anchor base c1_taps, repick, tap_ident, reach5). On zz_qf2_s29forms: out f8daa78e6faf (no RF); RF run in progress (rs_qf2s29rf).
Proof builds (QC-PROOF-1, epyc9 qc-proof-1, DO_NOT_COUNT, waived bind view ev2st_g1): 12-13 in flight. Failed on plan defects (listed above): coll_core, sle_fw_v3, sle_ctl cl503337ff (406,035 > 400k), cbn_q00 (relaunched with evidence). R-CAP census actual_std: cl372cea1c 388,806 / cla4f6f12f 390,644 / cl67434795 390,073.
Other children: QC-TAIL1-TRIAGE (run_station_tail1_regional.sh REGIONAL_STATION_MISMATCH edge 95 on main; first bad commit, functional or not). QC-FORMS-2 finding: the OT_QC_SWREG ifdef is missing in the _nb0/_orq copies of u_scale_wait (posted).
Open list (s30): u_ctl re-floor (win back the R-CAP cycles); monitor graph regen (133 bundles off reset endpoints); fw_v3 dr_ei/x_ctl_i long packed-lpad hops; su_l1 x_su_c_i 431.65 (verify on the kit); cap_estimate basis must be the current-form synth (RULES-CAP-1).

## 7 CURRENT STATE 2026-11-13 11:52 PST (supersedes section 6 where they differ)
- Train 62 claude/qc-region-1-1113 @9ccc9ce28f: count_align_plan missing --sta-plan regression fixed in code; READY posted. Full suite: identical 240 failure ids on branch and base 84dfcc6ec6, +12 passes = the branch's new tests (addendum posted).
- BLOCKER on QC-FORMS-2's forms plan 11618cec4513: cbn_q00 u_t00/u_t01 moved x +12.96 um (half M5 track) and the clock_entry_access footprints of the 9 moved entry cores were not moved. gen_phys raises "clk_c0 explicit entry off preferred routing track", so reset_steps RF=1 rs_qf2s29rf stopped at reach (RC 6). The no-RF output is f8daa78e6faf. 28 of 95 moved cores step x off the 0.064 track pitch. Asked for a re-emit with 1.728 um steps and moved footprints.
- COLL-HOLD: s29_final has FORMS_KEEP_TYPES (3 cbn_q00 types stay at s28 positions) and check_entries.py (exit 29) before reset/bind. Trunk dry run on s29reg: START 0, cland_mon 0; 122 START relays, 12 on the destination side (ctl->fe crossings take over the fed stage's EDGE_FALL; iverilog cycle-equal). Plans: 235dffe628e1; hand3 relay plan 982b17af9eb8 (G0/G0C 17/117).
  - Asked: top_rtl on the real bound top; lane-table rows for the 12 destination-side relays; dry runs on the T3a/T3b trunks.
  - ctl1 chain on the CTLCAP stem: hand re-compose (conflicts on coll_ft__cla4a25d77 and slw_su_c__cl19bb38ef).
- QC-REGION-1: s29reg gate FAIL (intra-region TT -151.32 ps; c_* early taps a median 546 ps late). T3a/T3b trunk_nodes written (epyc9 qc-region-1/s29t3a, epyc8 s29t3b; about 9.3k detoured legs, stage access max 387 um); GRT/STA running. K re-derive and the START-retime variants are running. Pick the s29 clock by gate + relay dry run.
- QC-FTGRID-1: grid-check branch claude/ft-site-grid-check-1113; asked to add a core-origin-on-track + entry-footprint-moves-with-core G0 check.
- Gotcha: a waiter that runs pgrep -f with the target pattern inside its own ssh command matches itself and never ends. Check the chain log's RC line instead.

## 8 CURRENT STATE 2026-11-13 13:34 PST (supersedes section 7 where they differ)
- s29 ETA: READY 2026-11-14 18:00 PST (posted to COORD several times). Critical path: HOLD-TAP-1 DME proof (needed by ~11-14 08:00).
- Ring choice is START retime (not depth-16). It runs only in region_form STA on a built proof. region_form @c38eedcb4c (claude/qc-region-1-1113) adds sync_count_straps and the retime default; --depth16-allow is opt-in.
- Knee: re-authored by me, delta 06fd6430b2a8 (epyc9 qc-s28-hf1c/bind/knee29). Applies on the stem hand 0427c6a3462d -> 3fffd9e7b186 and on the FORMS hand. +1 cycle on 4 lanes (x_fw_ctl 13->14, ag_eo/ard_eo 7->8, x_fw_stm_p1 4->5).
- Chains (COLL-HOLD, epyc9 qc-s29-reach):
  - ctl3/ctl4 strict bind FAIL BIND_RC=2 (strap 6 vs 7 bits; old region tool).
  - ctl6 = tree wt/qc-s29-tree2 @f9a49f6f86 (s29 tree + c38eedcb4c), script s29_final_v4.sh dd1f818ca4f5: hand reuse -> knee -> REGION -> STA (retime, PROOF switchable, default s29reg) -> Landings (exit 31) -> reach -> relays -> entries -> reset -> bind -> gates. Running.
  - ctl5f = FORMS with 5 kept types (3 cbn_q00 + 2 slw_su_l1, F-SUL1W schema errors). Running.
- Open: the new strap-site pin-record check (QC-REGION-1), and QC-FORMS-2 re-emit (cbn_q00 half track + F-SUL1W).
- Proof builds: once ctl6 passes G0 + bind, COLL-HOLD launches 10+ via ot-run on epyc4/intel1 (COORD order).

## CODEX notes 2026-11-13 13:49 PST — active QC takeover
- Direct takeover DIE-QC-100, QC-REGION-1, HARD-QC-FORMS-1/QC-FORMS-2 in existing trees. Healthy ctl6, ctl5f, DME STA and trunk dry-run retained.
- DME region STA completed at epyc9 qc-region-1/htdme2/sta_rep.json: crossings2525 FAIL0; depth4=2396/depth8=129; worst margins104.4/122.2; 684K changes; lane cycles5981->6495 across573 changed lanes;20 straps widened6->7 across8types. Numbers artifact-read, not independent signoff.
- New guarded kitwin_delta.py + htdme2/kitwin_delta.json/report in existing QC-REGION workdir:11852ports/125types;320 ports/11types need>208(max357). Candidate sets budget<=208 and PHY190, explicitly BLOCKED_CLOCK_ENTRIES;0cycles. Guard/idempotence passed. No closure claim.
- ctl7c private compose launched via ot-run epyc9 (intel2 client3969258, ~/qc100-codex-logs/ctl7c.log): reuses exact DME STA input hashes, applies KITWIN guarded delta, current trunk sites, reach/reset/strictbind. Source s29_final_v5.sh/run_ctl7_codex.sh in existing qc-s29-reach; existing v4/live jobs untouched.
- c_W1_bn_10 new clock form pilot2x2 uses existing region-dme-split, four local groups23/23/23/24taps with one core tap each; proposal viewed epyc9 qc-region-1/htdme2/split2x2_proposal.png. Verdict PASS-COND for kit generation only; new tree still needs visual review before GRT. ot-run epyc7 unit oth-ubuntu-549991-1794606482, intel2 client3953041 log ~/qc100-codex-logs/s29_split2x2_kit.log; stops WAIT_VISUAL after KIT. No new RTL/cycles/domain.
- Hard forms helper restored fsta3 actual compiled SWREG/PINKEEP proof launch (previous watcher selfmatched indefinitely); inherited launcher guarded against duplicate, no processes killed. SUL1 schema repair in progress.
- Token integration obligation: TOK-VERIFY-3/capture1113/latency_contract.json measures TLOADCAP resident install spacing90->91, first3->4/last90->91;stream+0/SWREG0. Carry into s29 event, no blanket per-token cycle claim.

## CODEX notes 2026-11-13 14:00 PST — QC failures diagnosed and fixes progressing
- ctl7c FAIL guard knee: it inherited the old pre-CTLCAP delta; fixed runner to knee29/delta_fwv3_knee_s29.json 06fd6430b2a8, retained failed directory, launched new ctl7d client3992895. ctl7d DME STA reuse + KITWIN + Landings pass; reach running.
- Repaired F-SUL1W: schema28->0, actual per-bit maxhop304.366um,0cycles; guarded delta6e18b5dfc08f; wrapper epyc9 hard-qc-forms-1/pipe/s29/codex_repaired/compose_qf2.sh. ctl8fc full forms chain client4042516(log~/qc100-codex-logs/ctl8fc.log), forms completed then hand recomposition. Includes track-correct CB.
- Signedhard-ring emission bug: old ctl4d EMIT gotDSREP1/RSTREP6 vs signed8/34. Shared/HBM fixed class commit79d58ec6f0(10focusedchecksPASS); cherry-picked only that commit existing QCtree2 d08b9a2edc, pushedhub claude/qc-s29-tree2-1113. No signedchild/interface/latency change.
- Old ctl4d strictbind32errors=30R8_STALE+PARAM_REGEN CS_RXVseam shifts1/2+hardringEMIT. Scratch R8derive demonstrates same+2 seam shift(validasbuilt2->4;slotsasbuilt3->5); no plan change needed. New isolated bind scripts keep per-run manifest/sidecar/R8 instead of racing runtime/sidecar_pv.json; not launched before finalreset. Final strictbind still required.
- Old QC-PROOF failures collected: cbf_q01 GRT overflow11749(H11748) hotspot1120,880..1140,900; cbn_q00cldbc GRT12740(H12739) hotspot1120,2380..1140,2400; HCIcl7d GRT26138(V25648) hotspot260,20..280,40(localdensity.805). CB badnet175083 is2-pin signal crossing hard u_t11 East->West viaR8pad, not clock/fanout. HCI soft-ring cramped area candidate is in forms worker. coll_n DRT0255 classified pinaccess/maze, no retry. coll_ftcla4a25d77 NOTSIGNED TT+25.34,FF-36.44/41,TTslew5226/FF106,large landing-select DRV class; noECO.
- Token worker full s28->DME2 price:1338changed lanes,+328aggregate lane cycles,max+5; BOUND model-only864cycles/token,4403.20->4389.29tok/s(-.316%). The earlier573/+514 was predecessor-to-STA, not s28base. Source price E9 tok-verify-2/qc_s29_dme2_price/price.json.

## CODEX notes 2026-11-13 14:23 PST — QC reach and floorplan fixes
- Reuse-writer shared solver ab145f3072 (17focusedPASS) picked into existing claude/qc-s29-tree2-1113 as1e3b302be8 and pushedhub. Actual4type fixed-phasepilot correctly FAILed insufficient2physicalstages for1187..1413um corridors. QCevent adapter proposes minimumphase growth rather than relaxing405um or changinggenericpolicy.
- Adapter rephase_reuse_writer_codex.py: full34reuse types schema/R1 PASS,0NOTFIXED,17writerphases+1/17unchanged,17readerdepthchanges; output tree2 plan_of_record/zz_reuse_rephase_all_codex.json/report. Mandatory postphase STA/K/reset/bind NOT YET PASS. Actual generated slw_fw_v3 writerphase4/3flop mechanism lockstep510checksPASS; bypass-last-stage mutantcaughtcycle6 (tree2/rephase_lockstep_codex/summary.json).
- postphase_chain_codex.sh runningE9 viaot-run client254551(log~/qc100-codex-logs/postphase1.log): REGION/STA/K afterallreachphasechanges, providerrelays, reset, FTgrid+CBmetadata, isolatedstrictbind. Earlieroldorder changed84logical STARTdepths AFTERSTA, so ctl7d notqualifiedasfinalevent.
- Foundmissed FTGRID_CMD: existing QC-FTGRID delta appliedCTLCAPbase privately390rows,scanFT offrow0,0cycles,1a3df->7c52ce4. apply_qc_final_geom_codex.sh foldsit and exactCB core_out_land_typestwo-current-name restoration intofinalcandidate beforeisolatedbind. Originalfailedlogskept.
- Clock split2x2pilot stillKIT/WAIT_VISUAL stage. New continuation qc_s29_split_continue.sh usescanonical exact833ps+both-edgehelper andmaxD8; refuseswithoutactualGEOM_REVIEW_PASS. NoGRT launchedbeforeview. Existingmeasuredproofs unchanged.
- SourcePINKEEP correction: fsta3 provesactualSWREG only (nb0 hadnoPINKEEPimplementation). NewREADY child claude/hard-qc-forms-1-tloadcap-synth-1113@95dd92ef230b fixesnormal+copiednb0 defaultoff0cycles; actualg_pin2048cyclelockstepPASS+mutant andsynth325shared->1300independentbits. Newfsta4actualPINKEEP+SWREG PLACE-onlyE4pilot client246803,log~/hqf-codexlog/fsta4_place.log.
- AdditionalCBF failure diagnosed: firstR8stage atE correctly,secondstageleftW byGPL,optionalcountmuxbreaksgenericchaintraversal. Candidate explicit E/N/centre corridor +1fixedPINcycle yieldsmax311.13um all514bits; notintegratedbeforecoherentbundle/model/exactness. Filepipe/s29/cbf_r8_corridor_candidate.json. HCIbandprivatebind+CBfirststagePLACEcanariesrunning;currentgeometrychecksremain.
- QC-TAIL1-TRIAGE historicalopenitem is alreadyCLOSED maintrain59/ae57355b16: benchdefaultPIN1+regionalmutantwitnesses; noRTLbug, nore-run.

## CODEX notes 2026-11-13 15:38 PST — clock calibration and strict-seed correction
- Actual 2x2 diagnostic completed: CA2525crossings0fail,minTT106.9/FF104.4; clockwindow still FAIL TTintra340.81/FF315.01ps versus208, seam187.20/171.81. No new clockbuild authorized from this. Exact legalized-site repricing localizes oldnode11122 mismatch: priceduniform209um stages actuallyinclude461um hop; deterministic +337psunderprediction. Existing --region-dme-actual-max immutablephysical_leg is next pure analytical estimate; shared owns bounded criticalregion estimate.
- postphase_chain shell completion was NOT strictbindPASS: inherited wrapper returnedtailstatus afterBIND_RC1. Corrected private runner toreturnactualrc, driver explicitlyrequiresbind_report andn_errors0. Failure1CMmanifestguard andfailure2nativeclocktableancestry retained; fixedisolation nowusesoriginalmanifestthroughguards thenperrun sidecar/R8/manifest INSIDEnativebase. Corrected stagedseed E9unit956055-1794612595 ELAB0,CM/KPguardsPASS,strictbindinprogress; noPASSclaim.
- ctl8fc fullforms chain stoppedentrycheck: CBNtypes622f65d2/d7bf7197/dbcda913 cores u_t00(+17.28,0),u_t01(+17.28,-51.84),u_t11(0,-51.84) movedwhileM5/M6/M7footprintsretainedoldposition. QCforms owns coherent guardedcorrection; noentrywaiver/retry.

## CODEX notes 2026-11-13 15:52 PST — coherent forms continuation and strict failures
- ctl8fc entry correction fixed27rectangles; entry check all18types PASS. Guarded incremental candidate97fbb1536aea preserves existing hand/R8/INNER and adds STMhome(+35logicalcycles), SUoutput4(+24logicalcycles), CBoutlandnames. Rephase all34types0fail, same17writerphase+1 changes; all34START geometry personally viewed, R1findings0, maxplannedhop402.061um. Private STA/K/reset/bind continuation admitted E9unit1077723-1794613342, log~/qc100-codex-logs/postphase_ctl8inc1.log; Q/continue_event_codex.sh. No clockqualification claim.
- Strict postphase_codex2_pre emitted34errors:30R8_STALE + dependentCS_RXVseam shift + twoTYPE_SPLIT(sle_ctl503337ff E3;67434795 W3) + truehardringEMIT cbn_q00dbcda913.na_i00 DEPTH8 bound vsDEPTH4signedchild. Driver stops onnonR8; no derive around these. QCforms owns actualD8child successor; QC/shared diagnose structuralOR/typecanonicalization beforetypecloning. Exactoldviews retained.
- Sourceclass RECTbug isolated b95a4c1b02 (hqf_apply.py only) pushed; actualF-CBdifference only27footprints. Merge lane notified toselectisolatedcommit becauseheldCBFparentchain. CBF source4ad3+b869+287bd nowcoversfullbankarea andactualsingleton span0 preservation; component PLACE stillneedscleanstrictpacket.

## CODEX notes 2026-11-13 16:16 PST — remaining QC blockers made concrete
- Full composed intermediate price s28->ctl8inc1:1350 changed existing lanes, net+487 lane cycles,max+5; class BOUND+900/token,4403.20->4388.71tok/s(-.329%). Replaces summing overlapping DME/STM/SU estimates; not native calendar price, future CBFfloor4 excluded. E9tok-verify-2/qc_ctl8inc_price/price.json.
- HBM normalized6563inputbits/14outputbuses: CTL E3/W3 splits are real input pad0 vscommonpad1,width456,fixed5 after ORrename; explicit private singleton type identities schemaPASS,0lane/cell/placement changes. Finalgeometry wrapper declares them; no binder guard edit.
- R8 scratch derive diagnostic FAIL34, but cause is carried AUTHORITATIVE cb16_pads extra: base table correctlybound20,extra overwritesbound21/pad12/landed33. HBM regenerates privately via baseline WITHOUToldCB16extra, retaincandidate_inner, then standingcb16_pads.py. Native-base R8_EXTRA_SPEC override nowcopiesperrunextratables afteroriginalCM/KPguards; globalruntimeunchanged. No manualtable edits/repeatedblindderive.
- Clock16region pureplanning andcanonicaljointpacking complete,noerrors/reach>250.15/16conditionalempiricalbounds<=208;W3bf00 fails241.6TT/223.5FF. Exactresidualpairt86/t9 bias209.5/188.7 comesfromlegal<=249umlegs withoppositesystematicstagebias,notlastmile;oneboundedhang-mode topology diagnostic running,noKIT/GRT.
- Corrected HCI count:fanout5670 isbuffer INSTANCE NAME,not5670loads. Root synchronousDFFQN->INV->BUFx8->64 D pins,75rootchildren; existingpads2/3/terminalcollocated. Guardedpadspreadproposal preservesdepth/terminalidentity,reducesbadfirsthop342->85.6um;root75/finitebankarea remainOPEN,noadoption. CBFhelperdiagnosis artifacts inHCIpadspreadgeomreview.
- D8child actualsynth22565cells/2860.36um2;realfaceguardcaughtmissing8-slottypedcontract,beingcorrectedbeforeP&R. FSTA5PLACE improvesmaxdensity.987->.919 butFTfinalNbank bypassedNSinputallocator; explicitopt-inextension/E-midbankrelocation ongoing. SUepoch envelopecorrected1.188->1.404um conservatively,samesites/cycles.
