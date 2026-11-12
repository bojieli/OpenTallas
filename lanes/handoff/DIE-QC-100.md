# DIE-QC-100 lane handoff (QC = qwen_compute die owner)  -- updated 2026-11-12 09:00 PST

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
