# S81-DIE-R3 handoff (Opus, succeeded S81-DIE-R2 / Codex 05:03 packet)

## State 2026-11-17 05:5x PST
- D5e HARD_CORE_PARAM_ALL with the honest bksel registry entry (OLL 2 RFH 2 HLAT 1, eco3 config.mk d77b25fd, records
  signoff 3a374028 + odb ac34039b; entry already in D5e/C4b tools/die_plan/hard_core_built_params.json a045d115) = REAL
  mismatch: die dsdv_bksel_q (rtl/dsrom_sys/s81_dv/unit/bk/dsdv_bksel_c.sv b281e1b5 = main) has only OLL (die 0);
  RFH/HLAT undeclared. RFH 2 = +1 input cycle. Recheck: E10 rows/f2s5_S81-DIE-R/d5e/hcparam_recheck_r3/ (and Codex
  params_recheck1117.json, same result). No waiver.
- D5e-r3 (in place in .../kw45/src_s81_pin_3c913dbdfb23_f2s4_cohort_d5e, not published yet):
  D5e + BA1 FWPPK signed (12 rows gunit_profile_delivery1117/ba1_fwppk_rows_vs_D5e.json, view dir copied) and the 20
  bksel rows reversed (bksel_signed_view_rows + bksel_actual_clock_budget_rows + c4/bksel_ck_m5_rows) + D5c pin ledger
  2467d3db. Plan 0e9e5c80 -> 9f664e6fa54a. Script E/tools/d5e_r3_rows.py, receipt E/d5e/r3/rows_receipt.json.
  Failed D5e out moved to E/d5e/failed_out_d5e_r1 (elab cache moved back).
- LIVE: E10 unit oth-ubuntu-1279075-1794923332, E/tools/bind_d5e_r3.sh (strict bind, LATCHECK, G0, PRE, gunit__t1
  pilot kit-rtl/prepare/GEN/kit_gen_lint), log intel2 ~/s81-die-r/bind_d5e_r3.log, outputs E/d5e/r3/.
- EGN overlay gen_phys c5e20297 already installed in D5e (Codex 05:1x).
- E = /srv/opentallas-scratch2/claude/s81-b3-clk/rows/f2s5_S81-DIE-R on epyc10.

## Next
1. D5e-r3 terminal -> publish (src_manifest publish/cached-receipt/links as tools/publish_d5c.sh) -> apply.
2. C4 on applied tree: C4R reset rows (lanes/handoff/S81-C4R-RESET-RELAYS-1117.tsv, strip relay_um 180), ordered rows
   e943f1f62f4 (S81-TYPES-R2), col/dsdv plain-posedge reset (150 measured col types first), + eco3 bksel with its RTL
   (RFH/HLAT dsdv_bksel_q) + die params OLL 2/RFH 2/HLAT 1 + priced +1 cycle + eco3 pin ledger bd1dc957.
