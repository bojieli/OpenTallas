# FABLE-RC-QC handoff (Fable 5.2; independent root-cause review, die QC; started 11-23 00:42 PST)

Brief: scratchpad fable_review_brief.txt + rules.txt + visual_brief.txt + visual_brief2.txt. Order: st_a, cb, su_l1/su_c, coll, hc/st_b. QC V4 cut ~06:00; V4 gaps due 05:00.

## State (01:3x PST; first-pass posts went out about 01:20, not 02:30)
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

## 01:3x update
- epyc7/epyc10 renders done and READ (clf4365a62, pvd2ec7769, pv4242de79): they confirm the st_a clusters. pvd2/pv42: (420-480,235-245) at the u_r0 NE corner / g_btb slit and (450-545,445-490) on g_btb[1]. clf4: (300-600,50-110) under the horizontal b_hw landing, plus (400-440,400-425) and (430-445,270-280).
- Reply FAM-QC-SLWSLE-R1 01:14: sle_hc1 pve230954c is SIGNED on its V2 attempt (no relaunch needed; my 'needs an owner' note is withdrawn). b_tw broadcast stations: SLWSLE takes them (asbuilt intra_stations). btab read stage is RTL in qfd_dv_s8x_btab plus a latency contract: NO OWNER yet. Pin registers measured TT mean 323 vs bound 280 (+43), FF 249 vs 227 (+22), n 5516. E-corridor seat check pending.
- Still no reply from VIS-QC, FAM-QC-CB-R4, OPUS-FIX-QC-COLL-R3, QC-PLAN-R13 (due about 02:20).

## 01:30 COORD RESUME (5-h limit cut ~01:17; Codex covered to 01:3x)
- CODEX-LOG handoff 01:19: COORD ruling for st_a = use STA-1b placement for the route wall, st_a wave rows stay held pending reviewed proof; the SRAM -> g_read arc is inside a closed core, so price an internal zero-cycle g_read re-seat BEFORE a +1-cycle successor (this supersedes my 'HCST takes +1 cycle' suggestion); b_tw slices mapped for bound intra_stations in parallel.
- COORD: QC-DIE-SEAT-1 ADOPTED, VISQC-DIE-1 DROPPED.
- No ot-run of mine is live (all renders done, self-reviewed 01:28). Nothing to relaunch.
- Reply FAM-QC-SLWSLE-R1 01:27: su_l1 hold -> V5 one-tap row after VIS-QC posts the SEAT-1 tap rule; su_l1 E channel -> V5 ft_slot re-site after the cl5ea486db GRT read (~03:00); su_c -> cap2b bind-clean, SU-2 with VIS-QC, pad-leaf stays optional. None is a built row yet.
- DUE 03:30: read replies (grep FABLE-RC-QC / RC-GAP in lanes/COORD-REVIEW-QUEUE.md), update verdicts in lanes/FABLE-RC-REVIEW.tsv, report the gaps still uncovered to COORD. Background waiter armed locally until 03:30.

## 02:25 FIX-LEDGER reasons (agent acd269758d3b62a53; lanes/DIE-FIX-LEDGER.tsv)
- rc97 + hg-QC-REACH: NOT accepted as closed (about -49 left < -42 gate, STA-1b unmeasured); deferral out of V4 accepted; stays OPEN, owner FAM-QC-HCST-R3.
- rc112: accepted. hg-QC-REPAIR-CAP: accepted as symptom, linked to SEAT-1c; DPL-0033 after repair on 4 st_a kits goes to the STA-1b row. hg-QC-CLOCK-NDR-DROP: accepted, probe must show 0 GRT-0273.
- V4 cut is now stated as 14:00 by FIX-LEDGER.
- 03:30 reply check still due; the local waiter may not have survived, so run it by hand.

## 02:55 COORD flow review: no V5 / no next event (post DEFERRAL-VERDICTS)
- Rejected deferrals: ledger row 71 su_l1 ft_slot re-site (SLWSLE) -> V4 row; row 69 cb landing bands (CB-R4/VIS-QC) -> V4 rows, gate by 13:00; slw_fe_v2 clf110fab2 core partition (V4-R2 745b777) -> not accepted without a measured TT setup >= -42 on the leaf-to-logic paths.
- QC no-launch 86 min: autopilot alive; 27 owner holds (17 cb, 6 st_a, 2 su_c, coll_core, sle_su_c). Needs owner: slw_fe_v1 cl08d14f0d stale 'kit busy'; phy_serdes_b ITEM-SYNC rc=2; slw_st_a_v1 pvdf8e5ca4 unheld and failing on CLAND band.
- Gate for all V4 rows: 13:00. Still due: 03:30 reply check + uncovered-gap report.
- 03:05 x7 slw_fe_v2 clf110fab2: ACCEPTED as REASONED on place timing (+6.2 worst, verified on epyc10 R6V3); reopen only if 4_cts_post_hook shows < -42 on a u_core leaf path.
- 03:10 rc97 ruling: CONDITIONAL ACCEPT for the cut (V4 cuts 14:00 with st_a held); hold releases on one measured SRAM->g_read setup >= -42 at 4_cts_post_hook on pvd2ec7769/pv88773f93/pv4242de79, from STA-1b+SEAT-1c probe (by 13:00) or btab_s4r harden. No measured REASON from HCST-R3 found on the hub.
- 03:15 rc97 clarified: for arm (b) the tile-level SRAM->q setup >= -42 in the btab_s4r kit 4_cts_post_hook releases the st_a hold, given strict bind + LATCHECK with the consumer patch; arm (a) keeps the type-level number.

## 03:30 reply check done (RC-REPORT-2 posted)
- Ledger QC: 4 REASONED, 12 ROW-DRAFT, 5 OPEN. Uncovered: rc97/hg-REACH (HCST-R3, unmeasured), rc96 b_tw (SLWSLE, no row/ETA), rc104+rc103 su_l1 rows not built (SLWSLE, c4 08:00), x5 DPL-0033 rerun, rc98 SEAT-1c tap row ungated.
- NEXT: (1) cross-check lanes/HOTSPOT-GAPS.tsv per-type QC items vs my rows; (2) re-check ledger ~08:00 (c4 start, sta1c bind) and ~12:30 before the 13:00 gate; (3) update verdict column in lanes/FABLE-RC-REVIEW.tsv as rows gate.
