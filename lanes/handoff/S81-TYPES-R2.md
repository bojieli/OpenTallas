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
