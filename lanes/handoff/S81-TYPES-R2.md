# S81-TYPES-R2 handoff (Opus successor of S81-TYPES-R; started 11-16 18:3x PST)

Owns S81 col / strip leaves / IFN0 halves. Predecessor files stay canonical for history: S81-TYPES-R.md (col), S81-TYPES-R-STRIP.md, S81-TYPES-R-IFN0.md.
Status script (localhost scratchpad snap.sh) = newest stage log per kit + client exit lines.

## 18:4x state
- COL gen/ (old regex, lead 40): h9_r2 / h9_r1 / h10_r2 in GRT on epyc8 (clients 687024-6).
- COL gen_rm2 ([._] relay regex): h10_r2 GRT (963708); h9_r0_p2 CTS read -131.4, 495 under -42, 557 of 659 on ONE pair bs1 -> e1_u_w xs_q (262 um, 4 buf, other bs->e pairs +31..+70; e1 pair is mirrored e|w). Route launched anyway for the GRT read (intel2 log pilot5rm2_col_h9_r0_p2_route.log). h10_r0_p1 in CTS (721643).
- COL gen_rm3 h10_r2 (regex + per-bit istations): CTS -39.0, 0 under -42 (an/p5rm3_col_h10_r2_cts); place LOOK PASS; route launched (pilot5rm3_col_h10_r2_route.log). Candidate to sign.
- Flow branch claude/s81-types-r-relayre-1116 @c0ddf60c174 (epyc7 coltap/repo): RELAY_MID_RE default [._] + test; gate log intel2 ~/fable-fix-s81-coltap/gate_c0ddf60.log.
- STRIP: t34 in CTS (intel1); t28 / t47 / t72 / t75 GP, t62 resize. t8fix GEN exit 0; kit image LOOKED (review_eight/t8fix.png): 0 macro overlaps, 0 ring-on-macro (was 14) -> PASS-COND; route client launched 18:35 (run_t8fix.log).
- IFN0: he_splitbal1 / hw_splitbal1 detailed route on epyc2.
- NEXT: GRT reads (an/stage_sta.sh KIT OUT grt) on every col kit; route DRC / TT / internal FF hold; visual review; sign-off; export both stores.

## 19:4x
- gen/col_h9_r2 GRT read TT -3.9 / overflow 0, then FAIL_POSTCTS exit 6 = pair_skew crash (ambiguous rs role on dsfd_bf_front_roots). Fix branch claude/s81-types-r2-psambig-1116 @430397fe1b0 GREEN 12/12, READY. h9_r2 kit pair_skew.tcl replaced (copy+mv, kit stopped; old = pair_skew.tcl.pre_psambig), FAIL marker -> FAIL_POSTCTS.psambig1, route resumed (log pilot5_col_h9_r2_route.log; failed log .fail1.log). Other col kits: patch the same way when they stop at the gate (source an/pair_skew_430397f.tcl on epyc8).
- COORD lever 2 fail-closed: claude/s81-types-r2-relayfail-1116 @fe26ef60b15 GREEN 63/63, READY. Relay unfitted counts: h9_r2 0/5, h9_r1 0/0, gen h10_r2 1/7, rm3 h10_r2 1/80 (u_lpl_17_r.u_y_q), r0_p2 16/91, h10_r0_p1 18/95.
- Stopped (exact PID / container mount check): rm2 h9_r0_p2 route (superseded by rm4), old F2s3 col pilots (epyc7/epyc8 containers), old l_t34 (epyc10), c_t75b (epyc8).
- rm4 h9_r0_p2 (bs1 moved) = evidence only (16 unfitted relays): read CTS bs1->e1 class, then stop it.
- bs-site row and h10_r0_p1 relay rows posted to S81-DIE-R.
- IFN0 halves: fork worker still alive and running post/sign-off itself (he signoff, hw signoff stage); do not duplicate.

## CODEX handback 2026-11-16 19:5x PST (Claude reset)
- PARKED safely; progressing jobs retained. No new physical sign-off or col-wave PASS claimed.
- **Urgent e5 dry-bind FAIL:** E10 s81-b3-clk/log/B6gF2s5e.log now ELAB_RC=2 after JSON backend. First action inspect run/b/B6gF2s5e/elab.log / out/asbuilt output. No adopt. C4 work remains separate.
- Col rm2 h10_r2 fresh reloaded-GRT TT FAIL -171.996 ps (2 paths), overflow prior0. Start u_u_t7/so[1:0] -> u_ist_frame_int_o0_0/q[383:382], wire1131..1320um, source700,58 -> end1391,473. Evidence E8 coltap/an/codex_rm2_h10r2_grt; admitted unit426818-1794886985 exit0, hub log codex_rm2_h10r2_grt_r2.log. Initial read-only client1980381 refused isolation; corrected client1987656 --dir parent, no kit modified.
- rm3 h10r2 GRT DB now exists; exact reloaded read not yet run. h9r2 resumed old-rule GRT advancing, h9r1 GRT advancing, baseline h10r2 DRT advancing. D4 source publisher fleet owns approved relay/psambig source; I did NOT launch D4 pilot yet. Generate h9r2 pilot from canonical existing prepared RTL on E10 after D4 publish, review, then route off E10. No col-wave1 release before qualified source/pilot.
- col_geometry worker found rm3 lone NOFIT u_lpl_17_r.u_y_q impossible at fixed endpoints: centroid L1~860 >810; possible final frame_int_i0 station move y565.92->~500, legal footprint still under investigation. Child canonical notes retain exact state.
- Strip B overlay E8 fable-fix-s81-cong/strip_xr_1116/overlay: XR writer907FF +1 HI +1 reset; smallest9951edge/33reset proof PASS, default XR0 equals old, bypass mutant fails cycle5. Selective mask propagation INCOMPLETE in real cap_end/ot_s81sl_slice_w3 and landed/c1x_k8_cap5r wrappers. Do not claim qualified whole B; fresh elab/bind required because VP flattened in kits.
- t47 source-hook actual-name fix branch ce1ca0f7e6 superseded cd9e0a184f (optional u_bound hierarchy prefix); initial replay moved spare28 only, primary-class successor replay pending. Do not approve ce1 alone. C4 geometry worker extracted SVC t6 stage9 row E/svc/t6_stage9_rows.json d2435a07,0cycles; waits strip masks.
- Core/IFN0/SVC and SerDes children wrote their canonical handback; fx6 current signoff started once, H3p real LEC started (old rc0 was echo only), MQ mutant5799/5799 temporal failures supports de6d approval.
- Hold carry evidence supplied: current819 D3 published gen_phys hash matches manifest35eaaa5d; actual diephase M7offset8.448, live PG_DIE_PHASE1. All16svc types equal F2s3; mig003 equal F2sv except later adopted FT rows. HOLDGEN applied exact event3fa87b84b18 to resolved four records; **carry these terms explicitly on C4 event or exact semantics rehold**. mig007 still held: coll_e current view LOCAL_PASS_NEEDS_PARENT, root to assess actual new view requirement.

## 20:3x update (COORD resume)
- D4 code-only source (D3 + c0ddf60 relayre, 430397f psambig, fe26ef6 relayfail) published E8/E10 exit 0, guard full_ok, atomic apply PASS via rt tools/autopilot/apply_reviewed_tree_marker.py. kit_wave s81 src = kw45/src_s81_pin_3c913dbdfb23_f2s4_cohort_d4 (manifest 4db2d3f87934). Receipt lanes/handoff/s81_atomic_apply_1794888904568170537.json. Controller tools-converge/s81/d4col_1116/finish2.py (DONE). Duplicate finish_claude.py (FIX-S81-COL-STALE) parked before apply, nothing applied by it.
- Pilot hold pilot-s81-4db2d3f87934: col-wave1 pilot col_h9_r2__t1__clce45cab5, release gen_pilot:s81:4db2d3f87934. NEXT: watch the wave pilot build on D4 -> GRT/route/DRC/TT/FF -> visual review -> sign-off -> export both stores -> only then post "col-wave1 PASS".
- rm2 col_h10_r2: GRT TT -172.0 = 2 endpoints u_t7/so[1:0] -> ist_frame_int_o0_0 q[383:382] rank0 (1,320/1,131 um). Site class; fix = rm3 per-bit sites. NOT retried. Posted.
- rm3 col_h10_r2: GRT gate crashed on pair_skew ambiguity (u_e15/rs), TT setup_est -9.55. Patched pair_skew 430397f by copy+mv, FAIL_POSTCTS -> .psambig1, route resumed (intel2 ~/fable-fix-s81-coltap/pilot5rm3_col_h10_r2_route.log).
- gen/ h9_r2, h9_r1, h10_r2 routes running (evidence on D3 kits); rm4 h9_r0_p2 at GRT (evidence only, 16 unfitted relays; do not sign).

## 21:5x update (FABLE-CLOSURE-STRATEGY 21:40)
- COL: FABLE-FIX-S81-COL owns col closure. Col volume stays held by result:S81-TYPES-R2:col-wave1/col-wave2; do NOT post those results unless FABLE-FIX-S81-COL says so. My D3 evidence kits (gen/ h9_r2 h9_r1 h10_r2, gen_rm3 h10_r2, gen_rm4 h9_r0_p2) are theirs to read/stop.
- D5 (in flight): dir intel2+E8+E10 /srv/opentallas-scratch2/claude/tools-converge/s81/d5_1116 (pack/, publish.sh, publish_epyc{8,10}.log, finish_d5.py -> finish_d5.log, DONE when applied).
  Content = D4 + r437 bind.py/test (3d763393b48) + form B tool r431/r432 (d1645b7afcd+1a183f5a920, 9 files) + event plan 819037bb + h2_2249/landed_sidecar_h2_psplit_all.json at in-tree paths; die plan path -> D5 tree.
  Apply: pilot gunit__t1; hold s81-strip-gpl-d5 keys ot_s81sl_leaf__* release result:S81-TYPES-R2:strip-gpl-tree; D4 pilot record retired (unreachable).
- NEXT: D6 = D5 + strip GPL sparse exit (39ef73a234f on 588ce81; tree face_flops.tcl already = 588ce81 version, gen_phys needs the 39ef73 hunk on the D5 gen_phys) once FABLE-FIX-S81-STRIP posts READY; then post RESULT strip-gpl-tree to release the leaves. Watch that gunit__t1 pilot GENs on D5.
