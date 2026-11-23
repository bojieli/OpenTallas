# OWN-QC-1123 handoff (11-23 ~02:10)
Rows from OWNERS-SWEEP a6ef39fb757.
1. sle_fw_v1__clf58b4dfb: DEAD-OWNER (VIS-QC-form_fefw stood down). Job RUNNING (ot-job on intel1 dir ot-jobs/sle_fw_v1__clf58b4dfb-route-key-cardinal-2843463-1795408598; CTS done 00:04, in GRT). Latest DB: 4_1_cts.odb (+3_5_place_dp). Cause spine-stacking (x_fe columns on spine y~710, 15 over-cap taps). VIS row DRAFT (VISQC-FEFW-1). NO ledger row, not in V4 -> sent to OPUS-FIX-QC-V4-R2 (a0667f53915fbc5a6); VIS-QC (a2e32d9bfa40faa1f) takes over the row. Do not cancel (can still sign).
2. sle_st_a_v2__pv4242de79, slw_st_a_v1__clfc5867a6(pvf82a6c28/pvdf8e5ca4): FAILED place, CLAND band hit by btab SRAM halo/wall + 8.9um slit. Covered by ledger rc94 (QC-DIE-SEAT-1a ROW-DRAFT), VISQC-STA-2; setup arc rc97 (FAM-QC-HCST-R3/STA-1b). VIS rows DRAFT -> no relaunch until PROBE-PASS. slw pvdf8e5ca4 is already running (gen).
Relaunch: after V4 cut 14:00 + PROBE-PASS.
TODO: recheck 13:00 that fw ledger row exists and VIS rows PROBE-PASS.
