# HEAD-HW-ECO handoff (child of HEAD-TYPES-R2; owns HEAD hd_host_w forms eco_hw4 + hw5) -- 11-16 20:0x PST

## RESET section (read first)
One signed form of hd_host_w is enough: whichever of hw5 / hw4e2 signs first gets exported (ffht_export.sh pattern, rtx-pro scratchpad copy).
- hw5 (structural: u_bout_coll_o0 bank on own tap clk_t6): GRT TT -0.92 FF +0.22 (Codex). Direct DRT LIVE E8 unit oth-ubuntu-473593-1794887144,
  client intel2 2033370, log ~/head-codex-logs/hw5_drt_ready.log; kit epyc8 /srv/opentallas-scratch2/claude/head-types-r/hw5/hd_host_w, run_drt_codex.sh
  chains 5_2_route..generate_abstract, pin audit, then signoff.py -> signoff_codex/ (log signoff_codex.log). DRT iter0 60% at 20:02. Do not restart.
  CTS note: OT_TAP_BALANCE left clk_t6 at mean 356 (346-472, 514 sinks) vs target 450.
- hw4e2 (eco_hw4/hw4e2, intel2 localhost unit oth-ubuntu-2066093-1794887221, client log ~/head-hw-eco-logs/hw4e2.log): route-keeping t5 PRD from i1t with
  OT_PRD_HOLD_PLAN=hei2/plan.tsv + patched kit_modes_eco.tcl. MEASURED in 5_1_grt.tmp.log: repair_design 249 buffers / 627 nets; setup repair
  -44.24 -> -31.32 session estimate (b_pay[260] still worst); "OT_HEI inserted 41 HB4 at 40 capture pins". DRT running 20:0x. MAX_PASS 1, OT_PRD_POST=0:
  sign off myself after finish (python3 -I hw4e2/signoff.py run --kit hw4e2 --base hw4e2/run/results/asap7/dp_hd_host_w/base --out hw4e2/signoff_e2).
- hw4e1 died at GRT (KIT_MODES single-mode tc guard). Kept as evidence.
- Branches: claude/head-hw-eco-staticplan-1116 @1ed0608cac GATE GREEN 3/3, READY posted 20:0x.
  claude/hold-eco-dump-units-1116 @54ee4a41c71 (dump x1e12 unit fix + plan refuses |slack|>1e5 ps): gate running, log intel2 ~/head-hw-eco-logs/gate_54ee4a4.log; post READY when GREEN.
- Old data: i1t signoff r2 TT -44.24, FF std -31.82 (port), internal -15.54 on 40 ends. hei2 plan: 40 ends, 41 HB4.
- Tools: own clone intel2 /srv/opentallas-scratch2/claude/head-hw-eco/src (+ worktree dumpfix); so_m516 = main 516226ace43 tools on E10/intel2/epyc8/intel1/epyc7.
