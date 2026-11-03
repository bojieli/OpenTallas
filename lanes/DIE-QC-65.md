# DIE-QC-65 (QC die owner, succeeds DIE-QC-64; started 2026-11-03 03:28 PST)
Helpers (short, fresh; collect predecessor jobs first; dirs epyc2:/home/ubuntu/scratch-root/claude/die-qc-6[345]-*/):
- /SUL: su_lane l0-l7 to sign-off (l2/l3/l5/l6 finish DONE 01:38-03:17 views exported; l0 finish in DRT, l4 finish live; l1 routed LEC (lec fix) live + resign_l1 waiting; l7 resign waiting on epyc2 load cap).
- /A0: NL re-sign (resign-qc64nl-lec live) + NK resume from synth (kit nk_ireg, lec EQ 36806/36806).
- /EV: RED child kit GRT (waiting), SC + GLUE delta re-run on the merged plan once ROOT-MERGE-24 merges RED 8247ff4ce24; SC = the 9 SC cell-cap types.
- /KITS: GPL-LOOP class (--gpl-plain, 29 retries attempt+1) outcomes, batch next class.
- /CLK: v1/v2 DME early-merge variants DONE (contracts 1734 -> 285 / 278) -> window re-derive + plan event.
- me: station parent-form estimate vs S81-PROUTE-2, READY/RESULT lines, rulings.
## log
- 2026-11-03 03:28 PST start. Collected: ot-run clients alive on intel2 (l0 finish, l4 finish, l7 resign, NL resign, RED grt, l1lec, l1 resign). epyc2 load 301/128 > 1.5x cap -> non-crit waiters stuck 4 h.

## EV
- 2026-11-03 03:55 PST start (DIE-QC-65/EV). State found: RED NOT on main (19af2d0dd06). RED child GRT50 is RUNNING (not waiting): ot-run client intel2 pid 1531818, epyc2 die-qc-64-red/red_grt_h0 started 02:05, in post-repair incremental GRT -> left in place. SC: 64/SC branch a0b2e425540 + uncommitted TRACK x 0.012 fix; its G0C on main plan = 0 errors (base 9 = the SC CORE-KS set); strict bind NOT run. GLUE: G0C 14 err vs base 9 (+5: glue_ft cells, glue.N/glue_ft.S 10.4 pins/um, START provider x2); ev3 stage1 re-run 00:36 not assembled; bench 3 seeds PASS.
- 2026-11-03 03:55 PST SC prepared on RED: epyc2 die-qc-65-ev/sc_wt branch claude/die-qc-65-sc-1103 = origin/main + merge RED 8247ff4ce24 (1582fffa369) + SC commits; delta1+delta2+G0C (docker qc65ev-sc-delta) and base G0C on RED plan 91ece1ff06b0 (docker qc65ev-g0c-base) running.
