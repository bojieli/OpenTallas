# HEAD-HW-ECO handoff (child of HEAD-TYPES-R2; owns HEAD hd_host_w forms eco_hw4 + hw5)

## RESET section (read first)
- eco_hw4/i1t (E10, replicas epyc8/intel1/epyc7 same path /srv/opentallas-scratch2/claude/fable-fix-head-types/eco_hw4/i1t): routed PRD t5, DRC 0.
  Old signoff r2: NOT SIGNED, TT -44.24 (16 viol; worst SRAM rb_safe bank[4] depth[1] -> u_ep.b_pay[260], long data wire wire33078->wire33077->D, slew 274 at D),
  FF std -31.82 (worst port coll_o0), INTERNAL (core) FF -15.54 on 40 ends. Parent ac92 re-sign (so_ac92) FAILED at once: incomplete tool bundle (only 3 files staged). Not rerun; internal FF already fails on the old record.
- Source tools: own sparse clone intel2 /srv/opentallas-scratch2/claude/head-hw-eco/src at main 516226ace43 (HOLD-FLOW-R lever 1 merged: hold_eco_internal.py, post_route_drv/hold_eco_internal_*.tcl, prd_mk OT_PRD_HOLD_PLAN). signoff.py there = ac92344e.
- hei1 (eco_hw4/hei1, E10+epyc8+intel1): FF/TT endpoint dump from the signoff_r2 session scenes -> hold_endpoints.tsv -> hold_eco_internal.py plan -> plan.tsv. Launched 19:1x via ot-run (intel1), client log intel2 ~/head-hw-eco-logs/hei1.log.
- NEXT: PRD pass hw4e1 = prd_mk i1t t5 OT_PRD_FROM=route + OT_PRD_HOLD_PLAN=plan.tsv, OT_PRD_NO_HOLD=0 appended (TT scene: setup margin 10 + targeted internal HB4 insert), MAX_PASS 1; then LOOK, sign-off with main bundle, export.
- hw5: epyc8 head-types-r/hw5 GOAL grt live (client intel2 306907), at CTS 19:0x. Not touched.
