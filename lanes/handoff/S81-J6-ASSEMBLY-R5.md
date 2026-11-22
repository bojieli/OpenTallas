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
