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
