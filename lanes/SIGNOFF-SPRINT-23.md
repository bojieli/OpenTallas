# SIGNOFF-SPRINT-23 (Claude) — started 2026-11-03 03:28 PST; successor of SIGNOFF-SPRINT-22 (died ~00:40 on limit)
Scope: raise signed hard-core count (56). Collect SS22 jobs; re-sign on flow-20261102-r-*; post-route ECO near misses first.
Workdirs: intel2 /srv/opentallas-scratch2/claude/ss22-resign (inherited), new: intel2 /srv/opentallas-scratch2/claude/ss23; census localhost ~/.claude/jobs/b7f906df/tmp/ss23.
Collected from SS22 (03:2x):
- ve_s q-s81 re-sign: signoff SIGNED TT +29.69/FF +8.70, post-route LEC KEEP FAIL (43609/43609 proved, 0 differ, 447 kept bits removed by eliminate_dead_logic) -> class fix = lec.py kept_functionally_unobservable (die-qc-64-sul, on main 19af2d0dd, NOT on r-tags) -> needs a tag carrying it (FLOW-24).
- HBM qctl q-hbm re-sign SIGNED + LEC EQ, counted (HBM 6).
- HBM query_static eco_loop m0: EXHAUSTED TT -2.21/FF +1.48/drv 2; t60: TT -3.17/slew 33 (i3 PRD pass). Not signed.
- HBM hcol_h1 eco_loop t60 intel1: admitted 23:44, status tbd.
Not mine (owners hold them; I count): KV pv_join R0/fMX + pv_pair (DIE-KV-62/drv chain, auto r-kv re-sign armed); HBM calendar_f20/vmdel_lr (DIE-HBM-59/LEAFSLEW: cal FAIL_POSTCTS insertion gate; vmdel_lr TT -25.78 slew 83).
