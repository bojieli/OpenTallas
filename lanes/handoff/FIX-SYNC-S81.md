# FIX-SYNC-S81 handoff (Opus; started 2026-11-22 01:13 PST). Memory across compression.
Brief: session scratchpad sync_brief.txt (+ family_brief.txt, rules.txt). Lane dir intel2 /srv/opentallas-scratch2/claude/fix-sync-s81.
Table: ~/coord/lanes/FIX-SYNC-S81.tsv (class_id, source, root cause, detection, fix form, evidence, status per family).
Deadline: J8 rows to S81-J6-ASSEMBLY-R5 by 11-22 14:00 (cut 16:00; apply 11-23 04:15).
J7 base: tree intel2 /srv/opentallas-scratch2/claude/kw45/src_s81_pin_3c913dbdfb23_d8j7_1117_work, plan physical/die_plan/s81/plan_h2_2249.json (a6771d121e95), bind physical/die_plan/s81/plan_of_record/native_bind/out.
Not mine: CLASS-SWEEP-R1 (HB4 over-insertion, band overlap, reset-copy tap), NEARMISS-ECO-R1, TAP-GRID-R5, family builds.

## Classes (see TSV)
S81-RAWRST, S81-REGSUM, S81-STNMACRO, S81-STRAP, S81-CAP400K, S81-FIXEDCYC, S81-FSTARTRST, S81-XMID, S81-LI3MID, S81-SEATKEY, S81-CHANSPREAD

## Log
- 01:15 reach_rules check die-wide on J7 plan: ot-run oth-ubuntu-3297674-1795338947 (intel2), out reach_j7_all.{json,tsv,log}.
