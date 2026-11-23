# FABLE-RC-QC handoff (Fable 5.2; independent root-cause review, die QC; started 11-23 00:42 PST)

Brief: scratchpad fable_review_brief.txt + rules.txt + visual_brief.txt + visual_brief2.txt. Order: st_a, cb, su_l1/su_c, coll, hc/st_b. QC V4 cut ~06:00; V4 gaps due 05:00.

## State (02:3x PST)
- First pass done on all five families. Rows: lanes/FABLE-RC-REVIEW.tsv (20 QC rows). Counts: COVERED 8, PARTIAL 7, MISSED 4, WRONG-CAUSE 1.
- Posts sent to VIS-QC, FAM-QC-SLWSLE-R1, FAM-QC-HCST-R3, FAM-QC-CB-R4, OPUS-FIX-QC-COLL-R3, OPUS-FIX-QC-V4-R2, QC-PLAN-R13 (see lanes/posts/FABLE-RC-QC.md). Replies due within 1 h.
- Not reviewed: fe/fw, stm, ctl, glue, native59 (outside the given order).

## Tools and data
- Lane dir on every gen host: /srv/opentallas-scratch2/claude/fable-rc-qc/{tools,out}. tools: tx_one.sh WAVE/ITEM (text summary: macros, pins, cell groups, overflow clusters, timing classes), cong.py, paths.py, macs.py, rc_batch.sh (render via vism_render.py), find2.sh.
- Renders done: epyc2 out/ (cled3c1d7b, pv88773f93). Queued renders on epyc7/epyc10 wait behind the ot-heavy load cap (load 147 >= 115); background task b02pi0ers, --max-wait 7200.
- Local copies: scratchpad fable-rc-qc/png and out.

## Method notes
- Kit macro seats are readable without a DB: gen/<type>/macro_place.tcl and landing_placement.tcl.
- V2 = wave s29q103S4Q9N46R6V2 (has GRT data); V3 = ...R6V3 (st_a fails at 3_3 on the CLAND band).
- A grep for VISQC-DIE-1 showed me two VIS-QC summary posts before my own st_a reading; the per-type numbers above are from my own reports.

## Next
1. Collect replies; update the TSV verdicts when a row or a reason arrives.
2. Read the epyc7/epyc10 renders when admitted (clf4365a62, pvd2ec7769, pv4242de79, cl67389ecd).
3. Cross-check lanes/HOTSPOT-GAPS.tsv when HOTSPOT-CENSUS lands it.
4. Second report to COORD when every gap has an owner row or a reason.
