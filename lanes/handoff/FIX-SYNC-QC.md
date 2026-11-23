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
- 02:2x RESUMED after weekly limit (posted). precheck+census done: epyc10 fix-sync-qc/pre_v3p7d (REACH errored: TAP-ERROR rt bins path), pgc_v3p7d/ABS-CENSUS.tsv (114 HOP).
- 02:3x r2 posted: lanes/handoff/FIX-SYNC-QC-V4-rows-r2.json (QS-LAUNCH cbx_q10 x3 y_o21 row; advisories sle_ctl x_fw_p2_i 432, cb window hops 425-445, CB-R4 station vs my inst_taps on cbn_q11 x_2_3 leg). Veto r1 to 02:50, r2 to 03:35. First COORD REPORT posted. No jobs running.
## NEXT
1. After 02:50 / 03:35: read posts for vetoes (FAM-QC-CB-R4, FAM-QC-FEFW-R3, FAM-QC-SLWSLE-R1); mark status in lanes/FIX-SYNC-QC.tsv.
2. After R13 06:00 V3 pick: recompose r1+r2 rows onto the pick (mk_rleg_draft.py / mk_launch_draft.py / strap_sites.py take BASE), re-run plan_gate_pre --baseline-plan pick, hand plan paths to QC-PLAN-R13 as V4 intake.
3. After the V4 tap compose (TAP-GRID-R5): re-run scan2.sh (reset_leaf_legs) for inst_taps drift (QS-ITAPDRIFT).
4. Harvest every 30-60 min (posts/handoffs of QC lanes + CLASS-SWEEP-R1); next COORD report ~06:3x.

## 11-22 18:1x resume state
- V4 intake (FABLE-FIX-QC-V4-intake.tsv): r1 QS-RLEG cbn_q11 = rank 14 L1; r2 QS-LAUNCH cbx_q10 x3 = rank 7 L1; QS-STRAP slw_fw NOT CARRIED (routing, setup -20.7) accepted.
- Running: QS-ITAPDRIFT check = reset_leaf_legs.py on epyc8 fable-fix-qc-v4/l0b_bound bind (pid 701854, ot-run), out epyc8 /srv/opentallas-scratch2/claude/fix-sync-qc/rleg_v4l0b.{tsv,json,log} (script scan_itap.sh B P TAG).
- Next: read rleg_v4l0b; off-consumer / >300 um rows -> reset_leg_plan re-pick -> rows r3 to FABLE-FIX-QC-V4 + QC-PLAN-R13 + FAM-QC-CB-R4. Same check on l1a_bound when FABLE-FIX-QC-V4 L1 bind lands (do not rebind).
- 18:5x: QS-ITAPDRIFT V4 done: cb-only reset_leaf_legs (scan_itap2.sh B P TAG TYPES, epyc8) = identical to V3 (10 off-consumer, 18 plan-legs); no r3 rows needed. Full-die reset_leaf_legs hangs (>60 min, cancelled): always pass --types. Next: same cb check on FABLE-FIX-QC-V4 l1a_bound when it lands; harvest loop.
