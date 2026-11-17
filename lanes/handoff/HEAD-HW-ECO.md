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

## CODEX takeover 22:18 result (2026-11-16)
- hei3 COMPLETE SIGNED: E8 eco_hw4/hei3/kit_hd_host_w/signoff_hei/signoff.json, TT -29.73, DRC0, FF core_n0/core_wns0. 444 output boundary negative ends (worst -31.91) remain advisory for actual parent proof. No RTL/latency change. Final placement image LOOKED; regular SRAM pairs keep aisles and pins, no new geometry defect.
- Export RUNNING via local rtx-pro /home/ubuntu/head-spe-export/ffht_export_v2.sh. Key s81_head/hd_host_w__hw4e2_hei3_1116, log local /home/ubuntu/head-spe-export/hostw_hei3_export.log; local archive files staged, alias PASS, AGIdock transfer follows. Check OK and both INDEX rows before declaring ARCHIVED-BOTH. Base has no LEF/lib; ILM/full real-die STA should use actual6_final V/SPEF/ODB plus kit/macros libs.
- hw5hei COMPLETE FAIL: DRC0, TT -47.65, FF internal3 ends worst -0.66 (all-path -30.09 output boundary). BeforeHEI TT -46.30 and internal38 ends -17.81. Worst setup is beat_tx[220] -> u_bout_coll_o0/q[220], data chain ~637ps after launch flop; tap6 capture ~330ps vs launch~426ps plus25ps source window. Dedicated bank tap failed final timing. Do NOT retry: signed hei3 already supplies host_w. Keep both failed records.
- NEXT: finish both-store export, notify HEAD-DIE-R to swap signed host_w into real4 and measure coll_o0 boundary hold. No further host_w P&R necessary.
- 22:26 CODEX export COMPLETE ARCHIVED-BOTH: hd_host_w__hw4e2_hei3_1116, ODBsha3605dde7658c39612d52993007e87be63ac39ea9e940702549e4b2fee9074846 size656037343; both INDEX appended. HEAD-DIE-R notified for real4 swap. Host_w physical closure complete.

## CODEX parent proof / fixed5-HB4 continuation 22:5x PST
- ORIGINAL signed hei3 remains ARCHIVED-BOTH; minimum ACTUAL parent now measured E7 head-hw-parent. Actual peer is abutting sst5.d_i. Regenerated host8 landing connections by existing real4 peer net identity (pair_bindings.json); complete513bits. TTsetup+760.925/hold-135.861; FFsetup+792.197/hold-116.621. Reverse515bits PASS FFhold+42.904. Original top/spine/ILM loads unchanged. Full regeneration failed only on missing unrelated serdes census sidecar; preserved evidence.
- Candidate E8 head-hw-eco/outpad5_fast2: 5HB4 at each513final output-buffer A pins; original BTerm/net identity untouched. Model microarch_model.json:2565cells ×0.10206=261.780um2 (~0.0625%slot),0FF/0cycles, FFminimum+149ps vs116.621deficit, TTmaximum664ps vs760.925budget. Source placement f3c465700de. Insert COMPLETE2565cells,1883fillers removed, exact oldslowprefix332/firstopt199 coordinates equal. LOOKED geometry_review.png, west band clear of macros; check_placementPASS.
- ROUTE live E8 unit oth-ubuntu-2503942-1794898390, intel2 client890877, log ~/head-hw-eco-logs/outpad5_fast2_route.log. Sourceflow outpad5_flow/run_fast2_route.sh, staged wrapper outpad5_fast2/run_route.sh; chains touched-net<=M7 route + fill/finish + local signoff_outpad5. No clock net changed. Earlier slow outpad5/outpad5_fast insertion units/containers stopped exactly after complete equivalent result; partial evidence retained.
- Source helper performance fix claude/head-hw-pad-search-1116 @f3c465700de GREEN5/5, READY posted. Actual10pad/2pin mutationPASS, lostnewcell mutantDETECTEDrc1;300Tcl candidate fixtures exact. Committed compactrecord lanes/handoff/HEAD-HW-PAD-SEARCH-result.json. Approval root.
- NEXT: routeDRC0 -> native V/SPEF/SDC from outpad5_fast2/kit_hd_host_w into E7 head-hw-parent_pad5/native. Pre-staged run.sh proves exact originalpin/port identity by collapsing2565noninvertingHB4 (+missing-alias mutant), extractsILM, measures SAME pair/spines. Do not export candidate until actual parent proof and local/block interface contract are qualified; original archives stay.

## CODEX closure 2026-11-17 00:2x PST
- BEST FINAL VIEW ARCHIVED-BOTH: s81_head/hd_host_w__outpad5_parent_1116, ODBsha4efcf1bacdb4fb5d225452dd0053100ceb9417929f1f564e7f1c46fd5c710ac1 size658802277. Local helper /home/ubuntu/head-spe-export/ffht_export_v2.sh aliasPASS71405buffers; both INDEX appended. New key supersedes hei3 for parent use; historical hei3 remains.
- E8 outpad5_fast2 local SIGNED: DRC0, TT-29.73, internalFFPASS; boundary-26.3 advisory. E7 head-hw-parent_pad5 actual host_w/sst5 pair PASS all513 coll_o0 outputbits: TTsetup385.539/hold131.311 FFsetup529.738/hold85.073ps. Reverse515 unchangedPASS. 2565HB4 added; graph equivalence original161630instances/pins/ports unchanged,0cycles; missing-alias negativecontrolDETECTED. Exact run/die_sta.json and buffer_identity.json retained. Route/job complete; no host_w heavy work live.
- Source native FF-only exact-cell anchor and explicit density consumer claude/head-lep-leaf-groups-1116@df3821c4cdd pushed, normalGREEN33/33(main17e5c950f49), ninefocusedtestsPASS, READY posted. Opt-in only; default40% and unrelatedgroups unchanged. Root owns adoption.
- NF15e capacity support delivered to other_types: measured macrohalo2um, row0.27/site0.054um, actualTAPCELL0.108x0.27 pitch25, ALL628candidateclockrectangles subtracted. 35group bank-split proposal initially MRD0 ZEROlegalrows due RX2bank4 halo, preserved failure. Corrected MRD0[916,643.5,948,655.5] PASS capacity364.88/reserve149.18. All28uniqueanchors capacityPASS; RIDhub2113.17/reserve631.17. Artifact intel2 head-hw-eco/lep_stage_capacity.json, script lep_capacity.py, reviewed image lep_stage_capacity.png. Projection for added same-width stages explicit. other_types owns remaining SRAM/bank reach and finalplan/G0/GEN. Capacity PASS does not assert missing internalmemoryrouting contract.
