# HEAD-HW-ECO handoff (child of HEAD-TYPES-R2; owns HEAD hd_host_w forms eco_hw4 + hw5) -- 11-16 21:0x PST

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

## 21:0x update
- hw4e2 FINISHED: DRC 0 (DRT iter 6), clk_check rc 0, 41 HB4 present (6_final.v HB4 23368 vs i1t 23327; cells tsv 41 rows). LOOK (intel2 eco_hw4/look_e2:
  wires.png/congestion.png, check_placement rc0): no new defect, macros as before. SIGN-OFF signoff_e2 (main bundle): NOT SIGNED: TT -29.73 PASS, DRC 0,
  internal FF -10.77 on 4 ends (was -15.54 on 40); port FF -31.91 (444 oports, the parent's).
- hei3 LIVE: second internal-only insert on hw4e2 (TP2/r417 recipe: dump in signoff_e2 scenes -> plan -> insert -> hold_eco_internal_route.tcl touched nets
  only -> kit copy fill/finish -> signoff_hei), NO setup repair. epyc8 unit oth-ubuntu-1340499-1794891646, client log intel2 ~/head-hw-eco-logs/hei3.log,
  dir eco_hw4/hei3 (replicas of hw4e2 on epyc8/epyc7). HEI_ATTEMPTED guards a repeat. intel2 scratch is below the 150 GB ot-run floor.
- hw5: DRT done, pin audit PASS 2723/2723, signoff_codex running (E8). Staged epyc8 /srv/opentallas-scratch2/claude/head-hw-eco/hw5hei/run_hw5hei.sh
  (same HEI recipe on signoff_codex scenes; launch with ot-run --dir /srv/opentallas-scratch2/claude --hosts epyc8 only after signoff_codex ends
  and only if internal FF < 0).
- STOPPED per COORD/FABLE-PD-HEAD-2045: hw4e1, further hw4 setup repair.

## 11-17 00:4x PST -- hd_host_w SIGNED (lane goal met)
- hei3 = hw4e2 + 4 HB4 (internal-only, touched-net route 7 nets, hei_drc 0, DRT 0 violations) -> fill/finish -> signoff_hei: R-MINIMAL SIGNED,
  TT -29.73, internal FF core_n 0, DRC 0; port FF -31.91 on 444 output-port ends = parent's (port_only_needs_parent). Kit epyc8 eco_hw4/hei3/kit_hd_host_w.
  Note: signoff drc_source is the copied 5_2_route.json from hw4e2 (also DRC 0); the hei route itself measured 0 (route.log, route/hei_drc.rpt).
- Exported BOTH: s81_head/hd_host_w__eco_hw4_hei3 (odb sha 3605dde7...; INDEX row 508). DUPLICATE: Codex exported the SAME record (same signoff sha
  0735b4c4...) as hd_host_w__hw4e2_hei3_1116 (row 509): count once. A later outpad5_parent_1116 (row 512) is the parent output-pad form.
- STA-1652: 40 warnings per corner, SPEF sub-nodes of the port net cland_fwd_fclk_out_coll_o0 not found (port-side forwarded clock net); internal gates not affected; open for HEAD-SPE-EXPORT seam check.
- hw5 + HEI (39 HB4): NOT SIGNED, TT -47.65 (9 ends beat_tx -> u_bout_coll_o0/q bank; clk_t6 tap left at 356 vs target 450), internal FF -0.66 on 3. Parked: needs a clk_t6 balance or setup fix, and COORD said no second hd_host_w rebuild.
