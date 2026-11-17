# HEAD-HW-ECO handoff (child of HEAD-TYPES-R2; owns HEAD hd_host_w forms eco_hw4 + hw5)

## RESET section (read first)
- eco_hw4 tree /srv/opentallas-scratch2/claude/fable-fix-head-types/eco_hw4 now on E10, intel2, epyc8, intel1, epyc7 (i1t, so, so_m516, hei2, hw4e1).
- i1t (routed PRD t5, DRC 0). Old signoff r2: NOT SIGNED, TT -44.24 (16 viol; worst SRAM rb_safe bank[4] depth[1] -> u_ep.b_pay[260]: t5 slew buffers wire33078/wire33077 sized on the placement estimate, routed slew 274 ps at D),
  FF std -31.82 (worst port coll_o0, the parent's), INTERNAL FF -15.54 on 40 ends. Parent ac92 re-sign FAILED at once (so_ac92 had 3 of 10 bundle files); not rerun.
- so_m516 = tools + physical/common_flow of main 516226ace43 (own sparse clone intel2 /srv/opentallas-scratch2/claude/head-hw-eco/src). HOLD-FLOW-R lever 1 is merged in main; signoff.py = ac92344e.
- hei2: FF/TT endpoint dump in the signoff_r2 session scenes -> hold_endpoints.tsv (1150 FF<0 rows, 26408 TT rows <600 ps) -> hold_eco_internal.py plan: 40 internal endpoints, 41 HB4, 0 partial, 1110 port paths skipped.
  BUG (repo tools/die_plan/post_route_drv/hold_eco_internal_dump.tcl): it multiplies get_property slack by 1e12, but the property is already ps -> slacks x1e12, plan gives 4 HB4 on every endpoint (hei1 shows it). My dump drops the factor. Owner: HOLD-FLOW-R.
- hw4e1 = prd_mk i1t t5, OT_PRD_FROM=route, OT_PRD_HOLD_PLAN=hei2/plan.tsv, OT_PRD_NO_HOLD=0 appended (TT scene: repair_design + setup margin 10 on routed SPEF, then targeted 41 HB4 insert), MAX_PASS 1, OT_PRD_POST=0.
  Launched via ot-run (intel2 client log ~/head-hw-eco-logs/hw4e1.log; physical log hw4e1/physical.log). E1_ATTEMPTED guards a repeat. Do not restart.
- NEXT: on finish: DRC from 5_2_route.json, LOOK (layout around inserts + b_pay path), sign-off with the hw4e1 bundle (main signoff.py) -> export if DRC 0 / TT >= -42 / internal FF >= 0.
- hw5: epyc8 head-types-r/hw5 GOAL grt live (client intel2 306907); not touched. At GRT: read OT_HW5_BANK_TAP, clk_t6 balance, TT/FF; then the same hold stage.
