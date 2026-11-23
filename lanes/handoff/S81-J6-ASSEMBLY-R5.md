# S81-J6-ASSEMBLY-R5 handoff (started 2026-11-21 18:4x PST; successor of S81-J6-ASSEMBLY-R4). Read R4's handoff first.
Work: intel2 /srv/opentallas-scratch2/claude/s81-j6-r5 (j7_apply.sh, pinsmoke.sh), stage intel2 s81-j6-r2-hub/j7_preferred_stage (marker_r5/, addpin_r5.py, addhold_r5.py, addhold2_r5.py). Lane clone epyc10 s81-j6-r4/repo.

## J7 apply (11-22 04:15 PST)
- Event record PUSHED main 18a2688b741f (physical/die_plan/s81/events/d8j7_1122/EVENT.json; replaces draft f176ced869d).
- Candidate lanes/handoff/S81_D8J7_source_candidate_1122.json (+ S81-D8J7-G0-BASELINE-1122.json): event 18a2688b741, manifest 12af64d4f18d, plan a6771d121e95, tools_sha 404887a342b0.
  - TOOLSKEW FIX: config.item_inputs[395 items].gen_tools_pin {event, src_manifest_hash, bind_out}, so wave kits gen/kit_rtl with the tree tools (byte-identical to rt 404887a342b0, the tools the bind was stamped with), and flow refresh still comes from rt/current. Without it every J7 kit dies at bind_toolskew rc 3: the wave runs the scheduler rt, not dies.s81.tools_sha, and the rt from dbf5266757ab (15:25) on differs in reset_replicate.py.
    Remove only with a strict rebind of J7 on a newer rt.
  - hold_records_add: j7-col-held-until-view-1122 (216 col; release proof:J7COL_UCF_VIEW, proof:J7COL_PLACED_READ, proof:J7COL_XO_KEEP_AB, tree_has_sha:ae660e1299; owner FAM-S81-COL-H10-R4).
    j7-serdes-no-start-1122 (11 serdes; release proof:S81_SERDES_START_ROWS_BOUND; owner FAM-S81-SERDES-R7). Proof terms = any lane's RESULT post "<name> ... PASS".
  - Dry apply on a scratch copy of the coord passed (pins 395, both records added, tools 404887a342b0).
- SCHEDULED: intel2 user timer s81-j7-apply-r5 (04:14:00) runs j7_apply.sh, writing s81-j6-r5/j7_apply.out: event_pending set, publish_apply apply --pilot-item dsdv_slice_lepe_mu_LP__t2, post-verify, hold restore if <100. A STOP clears event_pending and posts.
  To cancel: systemctl --user stop s81-j7-apply-r5.timer (on intel2).
- RISK: every non-hub gen host is DRAINING, and KW-FIX-45 refuses gen on intel2, so the J7 pilot gen waits for FLEET to undrain one host.
- Fallback candJ7enL6 (unit 3465054) only on a package defect.

## J8 intake (start after the apply)
LEPe proof10 (unit 258364), svc hi4 + 7 svc layouts, serdes START rows (lanes/handoff/FAM-S81-SERDES-R6-j8-serdes-start-rows.json, not yet bound), leaf RG9 re-grid (unit 1263880) and THEN a vp_sr_ho re-run + LF_CS_DEPTH vs a fresh ELAB, tap-sink rows, ft-slot re-site, col xo D3/D4, strip/body (FLOW-STRIPBODY-R2), FABLE-PD-S81-2000 START/reset reach as GEN (reach_rules.py fix; t46).

## 19:4x update
- J7 pinned-mode GEN smoke PASS on epyc9 (lepe_mu_LP t2 + svc_lo rs t1, preflight DRY-PASS; receipt s81-j6-r5/pinsmoke_epyc9/smoke_receipt.json).
- s81 gen_hosts now epyc2,epyc7,epyc10,epyc9 (FLEET). j7_apply.sh syncs candidate hosts to live gen_hosts (cand_live.json) so keep_gen_hosts holds.
- Waiter: local poll on s81-j6-r5/j7_apply.out (APPLY_DONE/APPLY_STOP).

## J8 intake add (20:4x)
- OPUS-FIX-S81-SVC-R9 J8 svc package: hi4 re-split (13409->8022 cut pins), 7 svc layouts, ft3 plan_ftresite_r9 sha 24dbfb31; gate tree intel2 opus-fix-s81-svc-r9/treeJ8; bind unit oth-ubuntu-618193-1795321900. J8 bind needs tools >= main 8ad54f25f4 (drop J7 gen_tools_pin at J8 apply). J8 FILE lines + epyc10 opus-fix-s81-svc-r8/j8/scoped_h8_overlay (sources + map_svc_j8_scoped_h8.json; asbuilt base = tree root).
- Successor after the J7 apply: S81-J7-HELD-R1 (COORD).

- J8 recipe: run intel2 opus-fix-s81-svc-r9/relay_r9.sh (die reset relay re-site: fW0_p1_b0 23->17, svc_13 relays, +31 boot cycles, max hop 290 um) before the J8 bind, with tools >= main 8ad54f25f4.

## J8 INTAKE LIST (posted 21:2x; full text intel2 s81-j6-r5/j8_intake.txt)
- Cut 11-22 16:00 -> one relay re-plan 16-18 -> one strict bind/LAT/G0/PRE 18-21 -> apply 11-23 04:15.
- Col entry: first of COL-H10-R4 / COLROM-R5 (5_1_grt.odb only) / BKSEL-R7 r7a with final-GRT TT>=-42 + ovf 0 by 11-22 14:00; else J7 col form.

- J8 add: slice_station__t37 pin-face re-site + sweep of all slice_station types for opposite-face pins (owner FAM-S81-SLICE-R6, by 11-22 16:00; GEOM-REVIEW 21:12).

- COORD 21:4x: S81-J7-HELD-R1 ended; R5 owns post-apply too (held rows, relaunch checks, first J7 wave launches). No handoff. SLICE-R6 resumed for t37 sweep, t46, t6.

- RELAY-INST 643ffb9932 (kit_istations: whole-station relay_sites keys): cannot enter J7 (pin = tree tools; newer rt => toolskew rc3 w/o rebind). Goes in J8 (rt >= max(8ad54f25f4, 643ffb9932)). Rec: keep col held until J8.

- COORD RULING 22:xx: J7 as sealed; 643ffb9932 -> J8. Col held until J8 UNLESS COLROM-R5 Kit B (OT_RELAY_MID_RE excluding u_y_xd_, J7 tools) shows xd stages <= 50 um from seats AND CTS TT >= -42 (post-hook) -> release col on J7 with that env as override (use item_env on col_* items, NOT die_gen_env, to avoid die_env_stale rearm of every kit) + remove hold record j7-col-held-until-view-1122. Post decision when Kit B reads.

- COL DECISION 21:5x: col waits for J8 (env-only Kit B cannot seat xd: key/flop mismatch + 52 merged u_w stations need 643ffb9932 + 8a2a7b31a9). J8 tools must include 643ffb9932, 8a2a7b31a9, 4dac1ad0b7, 8ad54f25f4. bk_sel 575 key re-key row owed by BKSEL-R7 (seat-miss-rows.tsv).

- J8 TOOLS (FLOW-OPS-R2 via COORD, hub 04baa8752e): bind J8 on main >= 5a966bb45bc (narrowed class keep: clock-landing ctrl regs out, relay/station/ROM-input/reset-sync kept; includes 643ffb9932, 4dac1ad0b7, 8ad54f25f4, aa0cde9d13). Verify 8a2a7b31a9 ancestry before the bind.

- POST-APPLY TODO (after pilot GEN PASS): release reps-first hold_items for c1x_C, kv_leaf t1-t4, seqhost, phy, iqf; convert 73 non-rep leaf from reps-first to J8 hold record with ETA 11-23 04:15 (owner LEAF-R7); svc stays split-pending. Coverage TSV s81-j6-r5/j7_coverage.tsv. Records carry eta fields.

- 23:xx: 12 hold records in candidate (all owner+ETA J8). Post-apply j7_apply.sh drops 342 reps-first/svc_* hold_items keys (reps_release.py) and writes j7_coverage.tsv. Release: gunit t1, iqf t1, kv_leaf t1, phy t1, seqhost t1. Dry: 52 LAUNCH / 343 HELD.

## 11-22 00:5x update
- BIND_STALE (SLICE-R6 t18): stale pair was the J6r1 bind + J7 plan in their spec. J7 in-tree bind: PROBE_BIND 0/395 stale; pinned t18 smoke DRY-PASS (s81-j6-r5/pinsmoke2_epyc9). j7_apply.sh now gates the reps release on s81-j6-r5/launch_ok (SET). seqhost__t1 smoke running.
- planref-missing (CLEAN-AGGR-R3): kit gen reads neither deleted dir; stage_hash_roots = hash-key text only (posted 8ddd67fb).
- J8 respace lever: epyc9 s81-j6-r5/j8_respace (ledger.json, famsplit.py, plan/ overlay 53cab071c82f, bind.sh -> ot_build.log, ob/). J7 has 0 hops >405; 2241 rows 300-405 vs CBC 300 target. Bind ot-run oth-ubuntu-3032603 epyc9. Compose rule for J8: family rows first, then istation_respace on the composed plan (owner rows win).

## 11-22 05:3x J7 applied + lessons
- J7 applied 04:20 (75fccc3c44f). Wave stalled 04:24-05:11: s81 bind_preflight first probe (395 items) blew the 15-min tick -> set dies.s81.bind_preflight=false (4b897fae7c4); re-enable after FLOW-OPS-R2 fix.
- LESSON: on S81 (every stops_off die, OWNER r703) hold_records do NOT block (hold_records.compile_holds skips stops_off dies); only legacy dies.s81.hold_items blocks. My J7 records held nothing and I dropped the 342 J6 hold_items -> 194 intended-held rows launched. Re-held 149 unlaunched as hold_items (34ed268e94e). For J8 holds: write hold_items keys (plus records for owner/ETA bookkeeping).
- COORD ruling 05:2x: serdes 8 cancelled (kit_wave cancel-rows --event 18a2688b741 --per-block STRUCTURAL); col 72 run with the measured stop rule (>=3 same-stage fails for hold reason -> cancel the remainder of that col class not past the stage); other 114 run.
- Pilot dsdv_slice_lepe_mu_LP__t2 passed gen + preflight 05:13, in place 05:16.

## 11-22 18:0x PST J8 (after weekly limit; Codex covered 11:xx-14:xx, notes intel2 s81-j6-r5/tmp/j8cut/RESUME.md)
- J8 cut v2 = no-SVC c67f4f6ba285 (SVC primary fails schema on 2 port windows -> J9). Respace -> J9 (bind FAILED 13:39). tap_grt_pre -> J9 (enters bind reset digest). MISC t5 band-clear -> J9 (t5 held).
- Gate run2: ot-run epyc10, intel2 log s81-j6-r5/tmp/j8cut/j8_cut_run2.otrun.log; script epyc10 s81-j6-r5/j8_cut_intake/j8_cut_run.sh (replan without respace -> j8_cut_gate.sh). Prints J8_GATE_GREEN.
- Then in order: epyc10 j8_stage_scripts/j8_seal.sh (relay_mid_re row + schema + PRE + pack + publish) -> j8_replicate.sh <gen hosts+intel2> -> intel2 j8_stage_scripts/j8_smoke.sh epyc9 <manifest> -> j8_event.sh <manifest> <plan sha> -> mk_cand_j8.py (template S81_D8J7 candidate; gate dir copy) -> copy cand to lanes/handoff/S81_D8J8_source_candidate_1122.json -> j8_apply.sh (posts APPLIED; unsets col OT_RELAY_MID_RE env; t5 hold).
- COORD: apply as soon as gate green (no 04:15 wait).
- 19:0x: J8 plan = f65f62779bef (c67f4f6ba285 + iq_C t1 / lepe_mu_LP t2 back to J7, PRE reprice 5 lanes; COORD 20:0x accepted). No replan (Codex replan broken). Gate run4b log intel2 s81-j6-r5/tmp/j8cut/j8_cut_run4b.otrun.log (run4 queued on --disk 150, client killed, relaunched --disk 60). Apply pilot slice_station__t18; apply holds iq_C t1 + lepe_mu_LP t2.
