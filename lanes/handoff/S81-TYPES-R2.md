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
