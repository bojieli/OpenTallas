# S81-DIE-R4 handoff (2026-11-20 ~10:50 PST)

Successor of S81-DIE-R3 + Codex. Rules: scratchpad rules.txt (hub intel2, ot-run only, no new holds except COORD stop list, 300 um, 833 ps).
My hub dir: intel2 /srv/opentallas-scratch2/claude/s81-die-r4-hub ; lane clone epyc2 /srv/opentallas-scratch2/claude/s81-die-r4-clone (events cone).

## J5 (14:00 cut) - armed, unattended
- All-gaps strict (epyc10, plan 8cf9560f) exit 11, exactly 11 EMIT: 8 col_h9_r2 R11 rows in bound-name form (u_u_bs10 -> u_bs10, u_t8, u_t6__payload),
  iq_C t1 xr c3 rb_v/rb_d source rows on an unconsumed port, serdes t1/t15 local FSTART copy depth 7/9 vs 13/12.
- Repair strict (Codex-prepared plan 913a7026, script epyc10 .../s81_j5_existing_clock_r4_1120/strict_r4_repair.sh, gate dir rehome_input/gate_r5_repair)
  running; log intel2 s81-die-r3-hub/j5_r4_repaired_strict.log. Donor watchers (vp_sr, rom, r1_frame, f0_q, svcref, t31) start at bound_ready; they
  are separate trial trees (go to J6 unless green in time), except svcref which writes into the bound out.
- j5_chain.sh (PID on hub, log s81-die-r4-hub/j5_chain.out): waits repair green -> waits svcref green -> reach check (every rtl/*.reset_tree.json
  tree.reach_um <= 300, j5_reach_check.py) -> seal bind _d8j5_..._bind_<stamp> on epyc10 -> compose src_s81_pin_3c913dbdfb23_d8j5_1117_work on epyc8
  (rsync link-dest D8i) -> replicate bind to 4 hosts -> publish_onbase d8j5 on D8i -> out_install verify 5 hosts -> event commit via
  mk_event_commit_r4.sh (R4 clone; R3 hwin clone has foreign tracked edits, that broke J3's push) -> mk_cand_d8j5.py writes
  lanes/handoff/S81_D8J5_source_candidate_1120.json + S81-D8J5-G0-BASELINE-1120.json, coord-commit -> CHAIN_PACKED + post.
- j5_apply.sh (log j5_apply.out): after CHAIN_PACKED: kit_wave_edit sets /dies/s81/hold_items {col_h9_r1__*, col_h9_r2__*} (COORD stop list: no
  120-kit col wave before J6 masters route), then publish_apply apply --pilot-item slice_station__t27, posts APPLIED. On any failure both post STOP.
- Known model-only risk: leaf HI bank rows in J5 raise leaf hot-tile demand 2-4x (spread model); J5 keeps them, GRT proof decides J6.

## J3
Not applied, superseded by J5 as the plan to apply; kits not cancelled; sealed bind _11200611 + review fence kept; bk_sel/t41 BAD/HOLD -> fixes in J5/J6.
Original optimistic publisher left parked. cw9b unit oth-ubuntu-3303151-1795193789 stopped per COORD (no cw9a/cw9b forms).

## J6 (11-21 14:00 cut)
- SDC envelope (per-port worst case over all 60 members per band; r1 W110/min67 45 ports, r2 W116/min68 40 ports; one item_env per band):
  epyc8 /srv/opentallas-scratch2/claude/s81-die-r4-e8/j6_sdc_env (src/, gen_out/, kit_wave_1120_reuse_env.json, envelope_report.json).
  Both pairs: pins/outline/sdc PASS, constraint/core_taps_ff/config identical, synth isomorphic, macro_place PASS; only pdn.tcl M8-grant comment hash differs.
- bin->lpad lockup (subagent): masters r1 col_h9_r1__t1__cl49d7a23e__pv1c15776f, r2 col_h9_r2__t1__cl774acf45__pv11b6518d at epyc8
  .../s81-die-r4-e8/j6_lockup/env_kits/<T>/gen/<T> (kit_zl_lockup: r1 2 latches 1490 b, r2 1 latch 1168 b, -DOT_ZL_LOCKUP, midpoint FIRM in istations.tcl).
  Synth queued on epyc8 (admits 0 GB). Open: synth + LEC latch_to_wire, latch->capture leg <=200 um check, then route both masters, then plan rows for J6.
- svc H8: goes to J6 if its R4 strict (S81-SVC-SPLIT client 2173093, width gate) passes; note t7 R9 max die hop 378 um > 300 to fix first.
- Slice C bundle-bug types (c1x_C t9/t10, iq_C t1) + svc mem_ar types on D8i: do-not-count rows verified present (7 hosts each), none in credit lists.

## Leaf GRT-TRIAGE lever (for J6)
- Cause both bands: shared 4-lane station stages placed at one centroid over the 16-lane array; 1,025-bit group buses fan out there (demand, not blockage;
  place_regions cannot help, flops FIRM). Rows: intel2 s81-die-r4-hub/S81-LEAF-SPREAD-J6.json (GS 0 restage + per-lane station sites, 288 rows/type,
  modelled peak -25..-68%). Open: t54/t35/t5 320 um first hop (needs vn_b next to vn_a, J7), t33/t46/t66 300.2, t44__clf4 small gain.
- Proof running (subagent) on epyc9 /srv/opentallas-scratch2/claude/s81-die-r4-leafspread/: tree_SP (spread, whole-die bind then t39 GRT) and tree_Cc
  (form-C control). Baseline D8i t39 overflow 80,858/58,705/54,150 (it5/10/20), top (1000,400) 29,297.

## col_h9_r0 sweep rows (owned, posted)
p1 pva2e3974f: src_manifest = D8i drift window (fixed 03:24, not flow); latest failure FLOW @place resize.tcl empty explicit buffer set -> FLOW-NOADV-0915.
p3 cl31d0dc4b / p6 pv0012ba28: CANCELLED geom SUPERSEDED, last guard ssh TimeoutExpired (infra). Not superseded by J6 (J6 = r1/r2 only).
All relaunch after the 405 reach override (lever 1) lands for D8i.

## Update 11:05 (COORD from FABLE-PD-S81-1100)
- J5 applies if bind green (no functional error found). j5_apply.sh now also holds every ot_s81sl_leaf__* type except the form-C representative
  ot_s81sl_leaf__t7 (hold_items via kit_wave_edit, re-set after apply if publish_apply drops them). NEXT OWNER ACTION: read t7 GRT at iteration 10,
  then release the leaf holds (kit_wave_edit --unset of those keys) if the overflow trend is sane. J5 raises leaf GRT top tiles (t7 station bits 4,190 -> 21,442).
- Stop: no hold-buffer ECO on col_h9_r0/col_h10 before one kit's hold ends are read.
- J6 fix list (ranked): 1 leaf per-lane spread rows instead of form C, incl t44/t53/t54 (S81-LEAF-SPREAD-J6.json; proof on epyc9);
  2 lockup rows for col_h9_r0 + col_h10 (96 types) plus the two masters; 3 re-derive reset relay form at 275 um (38 col trees lost negedge incl both J6
  masters: no J6 master route until bound RTL confirms negedge); 4 data hops to 300: serdes coll_o0 334-401, col_h9_r0 frame_int_o0, slice C, iq_C t1 416 leg;
  5 slice C taps: c1x t1 1,289-sink tap, kv512_C row; 6 SRAMREG: 0/75 leaf types carry it in the J5 base because VP_SRAMREG was staged only in the separate
  vp_sr donor tree (stage_vp_sramreg.py, gate_vp_sr) -> bring into J6 base; 7 bk_sel A3P rows (FABLE-FIX-S81-BKSEL-R2); 8 svc H8 (FABLE-FIX-S81-SVC-R2).
- Another waiter (s81-die-r3-hub/j5_r4_iq_output_map_wait.sh, 10:22, not mine) reads iq_C rb map after the repair bind; read-only.

## 11-20 12:05 update
- J5 repaired strict (gate_r5_repair): bind 0 errors, LATCHECK 0, G0 adds 85 errors vs D8i. 84 are clock_landings monitor hops (cland_mon_*, up to 5,005 um, 0 relays; D8i had 48 relay edges); 1 is the reset wavefront (38 partitions with no rst_o within 300).
  Cause: CBC rule 4 caps the die reset hop at 300 (reset_tree.relay_um); the landing monitor tree follows the wavefront; reach_relay_plan needs start_tree.provider (J5 existing-clock form has none).
  Accepted as non-functional (DECISION post 12:0x). J6 item 9: die reset hop 405 (die.reach_um), or die reset relays plus monitor relays.
- Re-armed after that decision. epyc10 s81-die-r4-relay/j5_pre.sh (PRE + touch rehome_input/bound_ready, via ot-run) -> hub j5_accept.log.
  The R3 donor watchers (svcref, t31, f0_q, vp_sr, r1_frame, rom) start on bound_ready.
  hub j5_chain2.sh (waits on j5_accept.log + svcref) -> j5_chain2.out CHAIN_PACKED -> j5_apply2.sh -> j5_apply2.out APPLY_DONE.
  The old j5_chain/j5_apply exited at CHAIN_STOP.
- Leaf t21 (a13) and t26 (a6) on D8i: GEOM VERDICT ISSUES-ACCEPT posted, released to route. No hold count is available at placement.
- svc_lo_dsdv_svc_rs__t6 is covered by FABLE-FIX-S81-SVC-R2.

## 11-20 13:14 J5 APPLIED
- S81 live = event 224567138ab, src kw45/src_s81_pin_3c913dbdfb23_d8j5_1117_work, bind ..._d8j5_1117_work_bind_11201213, manifest c75b12bc6707.
  Receipt lanes/handoff/s81_atomic_apply_1795209203163827642.json; candidate lanes/handoff/S81_D8J5_source_candidate_1120.json.
- Hold_items: 76 (col_h9_r1__*, col_h9_r2__* for the J6 masters; every ot_s81sl_leaf__* except representative t7).
- NEXT: read the t7 J5 kit GRT at iteration 10. If overflow is falling, release the leaf holds via kit_wave_edit (set /dies/s81/hold_items to just the 2 col patterns).
  If it is flat, keep the hold and fold the leaf spread rows into J6 (item 1).
- The pack chain stopped once on an ssh argv quoting bug in mk_cand_d8j5.py (fixed: script piped over stdin). It resumed via j5_tail.sh / j5_apply3.sh.
- Lockup subagent ended with jobs still queued: LEC, envelope synths, placement measurement. Paths are under epyc8 s81-die-r4-e8/j6_lockup.

## 11-20 13:2x COORD ruling (J5 accepted; J6 item 9)
- J6 item 9 = die reset relays plus monitor clock relays, keeping the 300 um rule.
  Fix tools/die_plan/reach_relay_plan.py to run on the J5 existing-clock form (no landing_network.start_tree.provider). Relay-tool agent launched 13:2x.
  Fallback if it is not ready by the 11-21 13:00 cut: die reset hop 405 for J6 only, relays in J7.
- Next: t7 GRT at iteration 10, then release the leaf holds; route the J6 masters.
- J6 rows to fold in (all under lanes/handoff):
  - S81-SLICEC-R3-J6-rows.json
  - lepe rows 4/5 (FABLE-FIX-S81-LEPE-*.json; confirm which files are "rows 4/5" in OPUS-FIX-S81-LEPE.md)
  - lockup station rows_s81_index.json
  - s81-svc-h8-j6-manifest-delta-1120.json (svc hslice dissolve + ties; R7 pending)
  - the FABLE-PD-S81-1100 ranked list (items 1-8)
  - item 9 above

## 11-20 13:3x COORD / FABLE-CLOSURE-1315 (J6 additions)
- (a) Core-pin stages on the worst wires of the held leaf kits: t60, t57, t43, kv_leaf t1/t4. First confirm whether the J5/J6 rows already station those hops (check the J5 bound relay rows plus the S81-LEAF-SPREAD-J6.json rows).
- (b) Slice C finish leg D=3 is required: no slice C build without those stages (check that S81-SLICEC-R3-J6-rows.json carries it).
- (c) Pipeline the cland START and the reset relay at 300 um. Leaf t72/t8/t56 are limited by single-bit cland_start / reset-relay nets through 13-26 buffers. Added to the relay-tool helper scope (in-type legs listed as J6 row data).
- (d) lepe row 4 plus the land.tag item.
- STOP: no release or cancel call from a post-place WNS when the worst slew is over ~1 ns; CORE-LIB-LIMITS-1330 is testing core-pin transition limits. This applies to the t7 GRT read too: judge it on GRT overflow and routed numbers, not post-place WNS.

## 11-20 13:5x OWNERS-SWEEP
- OWN posted for 52 held leaf rows plus t25 (DEAD-OWNER), all J5 representative-first holds.
- On leaf release: regenerate the kits so they carry the CORE-LIB-LIMITS-1330 320 ps core-pin slew limit (e7ebced0c4e). First confirm rt/current includes e7ebced0c4e.

## 11-20 14:0x FABLE-FLOW-1400
- (1) J5 gen units of t7 / kv_leaf t1 cancelled by exact name (pinned to eae58 without the slew fix); waiting for the wave to relaunch them on f2e64. Move them to epyc7 once FLEET-WATCH adds it to s81 gen_hosts.
- (2) Post-apply bind: elab yosys rc 137 at OT_POSTBIND_MEM=96. Rerun postbind-s81-1120135739 on intel1 at 160 GB (log ~/.local/state/ot-postbind/). If GREEN: publish_apply.py adopt-bind.
- (3) Staged: kit_wave_edit --set /dies/s81/die_gen_env/OT_PLACE_MAX_TRANSITION="320". Apply only when the CORE-LIB-LIMITS-1330 proof is green; flow_regen re-pins the unstarted J5 rows.
- RISK: die_gen_env OT_CBC_REACH_UM=405 vs J5 bound at 300. Watch the first J5 gen result for bound reset identity differs.

## 11-20 14:1x COORD on the 405 risk
- Gen solves each type reset under its bind-receipt cap (9172a65b43, eae5825732), so J5 300 um receipts win over the env.
- OT_CBC_REACH_UM=405 stays on s81 for the placed-hop estimator only; OT_RESET_HOP_CAP_UM is dropped.
- If a J5 gen still refuses with bound reset identity differs, post it to FLOW-NOADV-R2.

## 11-20 14:3x FABLE-FIX-S81-BKSEL-R2
- postbind-s81-1120135739: elab 0, bind running (intel1). Adopt if GREEN.
- J6 donor proofs after bound_ready (s81-die-r3-hub/j5_r4_rehomed_<d>.log): f0_q 0; vp_sr exit 11 (stale dead-input defines); rom bind 0, compare crashed on missing gate_r3/latcheck.json; r1_frame restore refuses internal_stations[].sites; t31 HI pack must be regenerated. A donor-repair helper is working on all four (epyc10 s81-die-r4-donors/).
- bk_sel rows 53956fe8b195 stay out of J6 until the successor delivers per-stage station sites + 11 face-bus stations + reset anchors. t41: no row needed.

## 11-20 15:2x FABLE-CLOSURE-1515 J6 order
1. Col master latch rows. The r2 env synth + 2 LECs were moved to epyc7 (outputs on epyc7 j6_lockup/*.e7.out); the r1 synths are still on epyc8.
2. reset/monitor relays: tool owned by RESET-RELAY-GEN-1530; my handoff is epyc10 s81-die-r4-relay/HANDOFF-RESET-RELAY-GEN.md (patch unpushed).
3. Leaf spread rows + core-pin stages.
- Lockup rows go in only after LOCKUP-STATION re-solves the taps.

## 11-20 16:0x MPL-0020 (FABLE-PD-QC-1600)
- The svc_rs MPL-0020 failures are all on D8i blocks (do-not-count, mostly SUPERSEDED). Cause: macro_place names macros in bound form (u_u_) and the netlist does not match.
- A watcher reads the 12 J5 svc_rs rows at floorplan_macro.
- If a J5 row hits MPL-0020: hand it to the FABLE-FIX-S81-SVC-R2 successor for J6. If clean: closed, fixed by J5.

## 11-20 16:2x
- Slew re-pin applied (kit_wave 9dcb613f): die_gen_env OT_PLACE_MAX_TRANSITION=320.
- ROM donor proof GREEN (bind 0, G0 0 new over J5, PRE 0). vp_sr, r1_frame and t31 binds are running slow on epyc10.

## 11-20 16:4x FLOW-NOADV-R3
- Leaf t2/t10/t52 reset-identity refusal cause: 9172a65b43 read per-type reach 180 as the cap. Fix pushed fa09197057, in rt 81c8692c1cdf.
- At the leaf release, include t2/t10/t52; add retry keys if REPEAT-STOP holds them (check kit_wave struct-list / repeat stops); confirm one clears gen and post it.

## 11-20 17:5x FABLE-CLOSURE-1730
- Holds applied (cfb64614): 32 route_hold_items + hold_items patterns: 29 monitor-pin types (scratchpad mon29.txt), seqhost__*, lepe/lepw LP. Leaf t7 is now held.
- J6 order: 1 source adoption (main proven source, hwin 8e20268b5d83 + seqhost reach row, RIP1 define, lepe rows 1-4); 2 monitor pin rows (S81-MONITOR-PIN-1745) + item 9; 3 col masters + latch; 4 leaf reset legs (tool) + SRAMREG + spread; slice C finish leg D=3. Re-pin tools to rt/current after a proof gen.

## 11-20 18:xx J6 donors GREEN
- epyc10 s81-die-r4-donors/<d>/j6_delta_<d>.json for vp_sr, rom, r1_frame, t31; f0_q green in the R3 gate_f0_q.
- vp_sr open items: real sites for the +1 ho station on 79 types (placeholder co-sited); compiler cycle table must add the SR VP cycles (kv_leaf t1/t3/t4/t5 included).
- r1_frame needs main 8e9cdd615c (schema sites) in the J6 tools.

## 11-20 18:xx SPLIT: J6 -> S81-J6-ASSEMBLY (handoff post 3fc2fac5). S81-DIE-R4 = J5 operations only.
J5 live: event 224567138ab, src kw45/src_s81_pin_3c913dbdfb23_d8j5_1117_work, bind ..._bind_11201213.
Open J5 operations:
1. Post-apply bind rerun: postbind-s81-1120135739 on intel1 at 160 GB (log intel2 ~/.local/state/ot-postbind/). If GREEN, run publish_apply.py adopt-bind. If not, diagnose.
2. Leaf representatives (released, kit_wave b07c9f34): t2 t10 t52 (1226 changed), t39 (1278 changed), t25__cl55642d17 (1226 unchanged clones), t56 (1356), t8, t28, t44__clf6cf8492. kv_leaf rep t1 is running.
   Leaf t7 is held: it is a monitor-pin type, 429 um.
   After each rep GRT is read at iteration 10 (judge on GRT overflow, not post-place WNS), release that class siblings from hold_items via kit_wave_edit --unset.
   Class lists: rerun the outline x station-change grouping (J5 vs D8i internal_stations).
3. Reset-cap check: confirm one of t2/t10/t52 clears gen without the reset-identity refusal (fix fa09197057). Post the result to COORD + FLOW-NOADV-R3.
4. svc_rs MPL-0020 watch on the 12 J5 svc_rs rows at floorplan_macro. Hit -> SVC-R2 successor. Clean -> close as fixed by J5.
5. Holds (kit_wave cfb64614): route_hold_items + hold_items on 29 monitor-pin types, seqhost__*, lepe/lepw LP__*; no route or retry until J6.
   Also held: col_h9_r1/r2 (J6 masters) and the leaf siblings.
6. Slew re-pin done (die_gen_env OT_PLACE_MAX_TRANSITION=320, 9dcb613f). No release or cancel from post-place WNS when the worst slew is over 1 ns.
Rules: cd / first; posts via bin/post.sh; kit_wave via kit_wave_edit; cancel only by exact unit; never cancel kits that can still sign.

## 11-20 18:4x
- Reset-cap fix confirmed: leaf t10 cleared gen (place), t2 in resume_fp, t52 in gen_lint.
- serdes t3/t4 DPL-0033 at detail_place (J5). Repro on epyc7 s81-die-r4-dpl/serdes__t4 (place.out); waiter armed. Plan cause -> S81-J6-ASSEMBLY + serdes lane; flow cause -> fix + relaunch t4.
