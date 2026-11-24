# FABLE-RC-QC handoff (Fable 5.2; independent reviewer, QC die only; RE-STARTED 11-23 19:22 PST as split of FABLE-RC-ALL)
Briefs: localhost scratchpad split_brief.txt, rules.txt, resume_1123b.txt. Parent: lanes/handoff/FABLE-RC-ALL.md + FABLE-RC-ALL-KV-QC-HANDOVER.md. Read-only except posts. Local notes: scratchpad/fablercqc (waiter wait_qc.sh, state file st).
## Jobs
1 V4 apply ~21:00 (QC-V4, apply_after_seal): check APPLIED hold set = 46 incl sle_su_l1__clc6d66f5b vs verdict d5c8db75 (8 hold groups).
2 QC-ALLFIX C1b 62ce8aba0292 gates (strict ~21:45, epyc11 cD) = B2 + CBN-RSF-SEAT + SUC-Q0 + SU2R-FIX1. Plan file epyc7 QC-ALLFIX/rows_c/plan_c1_fix1.json.
3 QC-RSN-PROBE: r2 GRT read of sle_su_l1__cl5ea486db (epyc8 private/QC-V4/sle_su_l1__cl5ea486db_1123172918; CTS post-hook +90.09, 5 hold viol pre-repair) + hold-lift proposal (release >= -42 at final GRT db) + x5 counts.
4 Review round on C1b kits: whole-die render + streets + type renders/STA/GRT; full-cause census per finding; post to QC-ALLFIX.
5 QC-TTC-RETIME (not QC-TTC-DEPTH): 20:30 bmath_retime.py, 21:00 depth census cap 14 on all flat cores QC+S81, 23:30 seq equivalence, 00:30-02:00 tt_ctlm probe, 03:00 ROW-REBASED.
## Open conditions carried (d5c8db75)
rc96 >= -42 final GRT on cled3c1d7b/cl67389ecd/clf4365a62; rc97 narrow btab parent (C2 ~02:00); rc104 x470-520 column < 90 %; x5 0 DPL-0033; su_c placement BAD until new form places clean; coll_core 205 reset copies connected post-CTS; coll_s routed LEC; glue/cb carry_0924; 0 GRT-0273 per overflow-row probe; F16 transport bound; tt_ctlm HELD.
## Log
- 19:24 TAKING posted (634713dc).
- 19:30 CONFIRMED by own read: CBN-RSF-SEAT 59991d13f2c3 is in C1b (6 points 552.96 -> 570.24 in cbn_q00__cld7bf7197); posted 21a2f202. Asked QC-ALLFIX for points_in_core before/after at C1b G0 (A had 48; 156 other inherited over-core sites remain per the row text).

- 19:45-20:30 posts: TTC-RETIME P1/P2 accepted (loops bind; physical CTS probe ~22:00 with un-keep; fallback loop register drafted in parallel). C1b G0 FAIL 3 (su_c cws2 stage-3 over macro) -> C1c 3b12251bfd6c gate of record (my diff: only 517 y values x 3 su_c types); strict on epyc7 cE ETA ~21:25; stm/sc probes from C1b bind cC valid. DEPTH-MAP: only tt_ctlm has a depth row; my depth rulings for glue (reach: rom_qr->dh_prog_a, u_record pair skew -101, embed_code_q; QC-GLUE) and sle_ctl (u_ctl/u_tap hard macros; binders rp->su_c station reach, x_hc1_st_b_i half-cycle, u_tap rst_n -106; QC-SLECTL-RESYN) WITHDRAWN. st_a C4 kit own read: x5 accepted; -59.92 = rc97 path (btab g_read -> u_r0), st_a held till C2. V4 apply slipped: SEAL_OK ~21:20, APPLY ~21:35 (fallback try1 bind). Owed to me: su_c over-core census + die points_in_core count + C1c render; st_a endpoint census; 7 station probe renders.
---- predecessor (pre-05:50) content below ----
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
- 03:40 rc96: FIX-QC-STA-BTW measured -218.27 at final GRT on cled3c1d7b (1073 um, 17 buf); form STA-BTW-0 (0 cycles) to be probed; PASS needs >= -42 at final GRT on cled3c1d7b, both hops shown (each ~520 um > 405), and siblings checked. Review row corrected.
- 03:45 rc96: per-hop estimate (hub 01fb016) agreed: hops 529/527 um close without stations (bank->r3 slack = 365 - bank tap). Acceptance still on the probe (>= -42 at final GRT on cled3c1d7b, cl67389ecd, clf4365a62), bank tap to be reported; re-read if SEAT-1c lands.
