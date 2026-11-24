# S81-OPEN-LEAFBAND handoff (Opus 5.5), updated 11-23 20:05 PST

JOB (COORD 19:2x): fix the c7a LAND-CAP finding (16 band x hard-core overlaps in 12 leaf types, 12 bands at fill >= 0.9) -> ROW-REBASED to S81-ALLFIX-INT for c8, due 21:30.

DONE
- Bisect (E9 /srv/opentallas-scratch2/claude/s81-open-leafband/bisect.log, lb_bisect.py): only step 03 leaf_allfix_1_r2near (8ce96cfc7c52) adds them. It moves all 27 hard cores per leaf type to C4 and keeps the B1 band rects. Step 10 KVLEAF v2 clears the kv_leaf t4/t5 ones.
- Row: E9 s81-open-leafband/ops_leafband_v1.json 8f2a6b3cedb4 (leafband_fix.py = cland_band_fit.resite, 16 ops). c7a+row e84259132859: LAND-CAP 0/0 die-wide.
- TGR5 (OPEN-CLOCK regen_c7a_b) composes with no conflict (band rects not touched by TGR5).

RUNNING
- E9 tail on c7a+row (lb_tail.sh -> s81-open-leafband/tail_v1, otrun tail_v1.otrun.log): relay/llr/fill/anchor/census/deadin repoint/PRE/LAND-CAP. Runs read-only against INT's tree tools.
- E10 fork of s81-j9-r6/amd1_tree -> E10 s81-open-leafband/tree (fork.log). Then lb_scope.sh applies overlay_e9.tar (the 110 files INT changed on E9 after its fork, sha list overlay_e9.sha), runs elab --strict, then a scoped strict on the 12 types.

NEXT: post ROW-REBASED S81-LEAFBAND-RESITE-1 with the PRE + scoped strict result. Clean-up: E10 tree and E9 v1/ tail_v1 via ot-delete once INT has composed c8.
