# FABLE-RC-S81 handoff (Fable independent root-cause review, die S81)
Brief: localhost scratchpad fable_review_brief.txt (+rules.txt, visual_brief.txt, visual_brief2.txt). J9 cut 11-23 12:00 (S81-J6-ASSEMBLY-R5); gaps before ~09:00 -> J9, later -> J10.
Output: lanes/FABLE-RC-REVIEW.tsv (die,family,item,your_cause,covered_by_row,verdict,evidence_png). Posts to owning VIS/family lanes for MISSED/PARTIAL/WRONG-CAUSE.
## State
- 11-23 00:45 START. Family order: leaf (main thread) ; forks: COL-A (h9_r1,h9_r2), COL-B (h9_r0_p*,h10*), SLICE (dsdv_slice*, slice_station), SVC, MISC (serdes,bk_sel,iqf,gunit,eng,seqhost,phy).
- Forks return TSV rows to the main thread; main thread alone writes FABLE-RC-REVIEW.tsv. Forks post gaps to owner lanes under lane name FABLE-RC-S81.
- Own-view notes (before opening VIS-COVERAGE): intel2 /srv/opentallas-scratch2/claude/fable-rc-s81/ownview/<group>.md
- 11-23 00:59 LEAF done: 11 rows in FABLE-RC-REVIEW.tsv (6 COVERED, 3 PARTIAL, 1 MISSED, 2 WRONG-CAUSE incl kv_leaf); 2 RC-GAP posts (LEAF-ROUTE-CBC: ft street, junction tap pile, kv_leaf estimator-only; OPUS-FIX-S81-LEAF-R10: lpad reset recovery, SRE-SRC scope). Waiting on forks COL-A, COL-B, SLICE, SVC, MISC; then first-pass report to COORD; then chase replies (1 h SLA).
- 11-23 01:00 SVC done (fork): 14 rows (1 COVERED, 5 PARTIAL, 8 MISSED); no placed/GRT DB exists for any svc type except the two hi4 pieces; RC-GAP post to OPUS-FIX-S81-SVC-R9 (hub ca5e3bca65a).
- 11-23 01:02 SLICE done (fork): 12 rows (2 COVERED, 6 PARTIAL, 4 MISSED); 4 RC-GAP posts (885c479f, c5c23eec, 158d0db8, 715b06a8). Waiting on COL-A, COL-B, MISC.
- 11-23 01:03 MISC + die done (fork): 30 rows (9 COVERED, 8 PARTIAL, 10 MISSED, 2 WRONG-CAUSE, 1 N/A); 5 RC-GAP posts (serdes clk skew, serdes other, eng, seqhost/gunit/bk_sel internal reach, die sparse-core clock). Waiting on COL-A, COL-B.
- 11-23 01:03 COL-B done (fork): 18 rows (7 COVERED, 8 PARTIAL, 3 MISSED); posts 441be017, 96afb378, 0c4528f0, 314c2b14. Waiting on COL-A only.
