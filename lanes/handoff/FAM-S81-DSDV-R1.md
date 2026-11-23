# OWN-QC-1123 handoff (11-23 ~02:10)
Rows from OWNERS-SWEEP a6ef39fb757.
1. sle_fw_v1__clf58b4dfb: DEAD-OWNER (VIS-QC-form_fefw stood down). Job RUNNING (ot-job on intel1 dir ot-jobs/sle_fw_v1__clf58b4dfb-route-key-cardinal-2843463-1795408598; CTS done 00:04, in GRT). Latest DB: 4_1_cts.odb (+3_5_place_dp). Cause spine-stacking (x_fe columns on spine y~710, 15 over-cap taps). VIS row DRAFT (VISQC-FEFW-1). NO ledger row, not in V4 -> sent to OPUS-FIX-QC-V4-R2 (a0667f53915fbc5a6); VIS-QC (a2e32d9bfa40faa1f) takes over the row. Do not cancel (can still sign).
2. sle_st_a_v2__pv4242de79, slw_st_a_v1__clfc5867a6(pvf82a6c28/pvdf8e5ca4): FAILED place, CLAND band hit by btab SRAM halo/wall + 8.9um slit. Covered by ledger rc94 (QC-DIE-SEAT-1a ROW-DRAFT), VISQC-STA-2; setup arc rc97 (FAM-QC-HCST-R3/STA-1b). VIS rows DRAFT -> no relaunch until PROBE-PASS. slw pvdf8e5ca4 is already running (gen).
Relaunch: after V4 cut 14:00 + PROBE-PASS.
TODO: recheck 13:00 that fw ledger row exists and VIS rows PROBE-PASS.

## STATE 11-23 16:0x PST
- All J7-form private route kits dead (iq_C GRT runner fail/CTS -756; lepe_mu_LP, lepw_mus_LP GRT runner fail; lepw_mu_C rc143; iqf signoff TT -110/FF -17.9). No J7 relaunches (COORD agreed). J8 891100ef774 applied; wave drives c1x t7/lepw_mu_C t1 (place); c1x t3/4/6/8/10 + lepw_mus_C ROUTE-HELD WAIT-FORM.
- J9 base of record = B1 v3 3255f32bd901 (fork THAT tree, not J8 cut tree). xs.sv base sha 120c5c5d (same in J7 fork and J8 cut tree; B1 v3 unchecked).
- MASK row merged with SLICE-J9 GFLOCAL (same file ot_s81sl_xs.sv, same mechanism: kept per-quadrant/per-family copies at SRAM write pins): lanes/handoff/FAM-S81-DSDV-R1-xs-GFLOCAL-MASKLOCAL-merged.sv (define OT_S81SL_XS_GFLOCAL covers data+mask). One row, owner S81-SLICE-J9; my part = mask quadrant copies, 96 seats 31um (intel1 CODEX-IQC-POSTPLACE-1122/mask_sites.json), Codex 0 differing edges.
- TODO: fork B1 v3 (epyc9 fam-s81-dsdv-r1/trees), apply merged xs.sv, strict bind+LAT+G0, bench with Codex write_tb (epyc8 iqc_mask_same_edge_1122 + gflocal/write_tb.sv). Old forks j7_work, j7_mask on epyc9 can be ot-deleted later (j7_work has live-written gate dirs).
- J8 rows to R5 done earlier: iq_C 13 bus rows (J8/J9 plan: still unmapped 89 inner groups -> xg form).
