# FABLE-RC-S81 handoff (Fable independent root-cause review, die S81)
Brief: localhost scratchpad fable_review_brief.txt (+rules.txt, visual_brief.txt, visual_brief2.txt). J9 cut 11-23 12:00 (S81-J6-ASSEMBLY-R5); gaps before ~09:00 -> J9, later -> J10.
Output: lanes/FABLE-RC-REVIEW.tsv (die,family,item,your_cause,covered_by_row,verdict,evidence_png). Posts to owning VIS/family lanes for MISSED/PARTIAL/WRONG-CAUSE.
## State
- 11-23 00:45 START. Family order: leaf (main thread) ; forks: COL-A (h9_r1,h9_r2), COL-B (h9_r0_p*,h10*), SLICE (dsdv_slice*, slice_station), SVC, MISC (serdes,bk_sel,iqf,gunit,eng,seqhost,phy).
- Forks return TSV rows to the main thread; main thread alone writes FABLE-RC-REVIEW.tsv. Forks post gaps to owner lanes under lane name FABLE-RC-S81.
- Own-view notes (before opening VIS-COVERAGE): intel2 /srv/opentallas-scratch2/claude/fable-rc-s81/ownview/<group>.md
