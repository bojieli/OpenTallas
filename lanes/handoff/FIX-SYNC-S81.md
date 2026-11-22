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
- 01:35 POSTED S81-RAWRST non-leaf rows (rr/, PRE PASS); 01:36 S81-FSTARTRST svc rows (fs/, PRE PASS on SVC treeJ8). Veto windows 03:30 / 03:45.
- 01:4x-02:1x weekly limit. 02:19 strict gate relaunched: ot-run on intel2, script gate_rr.sh, log grr.otrun.log, outputs grr/, tree gtree (J7 fork, plan swapped to rr/plan_rr.json). Markers FSRR_ELAB/BIND/LAT/G0/PRE/REACH, FSRR_GATE_DONE.
- 02:3x POSTED S81-FIXEDCYC IQF rows: iqf/j8_iqf_rows_repriced_delta.json 80ee97685c3b (reprice 5 lanes). Open Q to IQF-R1: duplicate conn bus:idx_o0.
- Other J8 row files: LEPE-4 drafts (owner strict binds), SERDES start rows (owner gate PASS), BKSEL (positions), SLICE strip-body (proposal), CLASS-SWEEP C rows (tap_reset_split; theirs).
- TODO: post gate result; serdes stations inside u_phy slot advisory -> SERDES-R8; CHANSPREAD scan (relay_sites y-line density) on other types; 4-h report to COORD (first report after gate). Re-scan final J8 compose when R5 publishes it.
- 04:00 RAWRST strict gate GREEN (grr/: bind 0, LAT 873/873 no change, G0 0 new, PRE PASS, reach5 non-leaf only kv_leaf t3 = LEAF-R10). Posted RESULT + round-1 REPORT to COORD 04:0x. No vetoes on any row set.
- NEXT: when R5 publishes the composed J8 plan (after 16:00 cut), re-scan: reach_rules check rule 5, fstart_scan.py, plan_gate_pre --baseline-plan J7; answer merge questions; next 4-h report ~08:00. gtree (54 GB) can be ot-deleted after J8 bind if not needed.
