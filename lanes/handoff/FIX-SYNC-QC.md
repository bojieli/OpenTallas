# FIX-SYNC-QC handoff (Opus; started 2026-11-22 01:13 PST). Brief: scratchpad c228d9e1 sync_brief.txt + family_brief.txt + rules.txt.
Job: harvest accepted QC fixes -> classes in lanes/FIX-SYNC-QC.tsv; detect each class on every other QC family (static plan first, placed DBs only if needed, never build to detect);
draft rows (plan_gate_pre --baseline-plan, tools >= fda4eaad0e), hand to family owner (1 h veto) + QC-PLAN-R13 as V4 intake AFTER the 06:00 V3 cut. Never touch R13 V3 binds.
Report COORD <250 words after first round, then every 4 h.
## Work dirs
- epyc10 /srv/opentallas-scratch2/claude/fix-sync-qc (scan1.sh = precheck + plan_geom_census on V3 candidate plan; outputs pre_<TAG>/, pgc_<TAG>/).
- V3 candidate plans: epyc10 qc-plan-r13/v3p6/plan_v3p7{d,d5,c,b2}.json (pick at 06:00: d5 > d > c > b2 > n3). Detection base = plan_v3p7d.json until the pick.
## Owners (COORD-ROUTED-OWNERS + handoffs)
cb*/cbx*: FAM-QC-CB-R4. coll_core/coll_ftc: OPUS-FIX-QC-COLL-R3. hc/st/su: FAM-QC-HCST-R3. hc0 splits, su_c, sle_stm, tt_ctlm: FAM-QC-SLWSLE-R1. fe/fw: FAM-QC-FEFW(-R3). sle_ctl/sc: QC-SLE-R5 (check live). glue*: TAP-GRID-R5. Plan: QC-PLAN-R13.
## Do not duplicate: CLASS-SWEEP-R1 (HB4 over-insertion, band capacity, reset copy tap), NEARMISS-ECO-R1, TAP-GRID-R5 (tap density/splits).
## Log
- 01:13 RESUMED posted. 01:2x scan1 (v3p7d) launched via ot-run on epyc10 (client pid 3088555, log scan1.otrun.log).
- 01:5x r1 DONE: lanes/FIX-SYNC-QC.tsv (11 classes) + lanes/handoff/FIX-SYNC-QC-V4-rows-r1.json (QS-RLEG cbn_q11__cl5cc92dfe inst_taps 89->90; QS-STRAP slw_fw_v1 cl592e3d37 + optional slw_stm_v1). Posted to CB-R4/FEFW-R3/R13, veto until 02:50.
  epyc10 fix-sync-qc: detect_slit.py, detect_landface.py, detect_launchwire.py, mk_rleg_draft.py, strap_sites.py (= S81 slice_strap_sites.py), rlp3/ (reset_leg_plan V3 numbering), in/<type>/ (V2 geom + bound sv copies).
- Next: QS-LAUNCH cbx_q10 x3 y_o21 station re-site (363->246 um, 0 cycles; site found core-free); precheck REACH diff vs handed V4 rows; sle_ctl lever-3 type still has x_fw_p2_i launch hop 432 um (> 405) -> tell SLWSLE.
