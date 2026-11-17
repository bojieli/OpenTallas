# HEAD-SD9A — hd_serdes form sd9A to R-MINIMAL sign-off (child of HEAD-TYPES-R2)

## 11-16/17 ~03:00 PST state
- sd9A GRT (epyc7 .../head-types-r/sd9a_grt1/hd_serdes) EXIT 6. Measured full TT list on 5_1_grt.odb (kept TT-repaired DB, GRT RC frame of
  tt_setup_repair.tcl, ot-run epyc7, outputs sd9a_grt1/hd_serdes/sd9a_meas/{tt_viol_end.rpt,tt_top40.rpt,pos.tsv}): wns -189.61, 47 endpoints.
  - Family R (reset/start relays, 8 endpoints, -81..-190): start_o_0 -189.6, rst_o_0 -187.9, rrl_32->33 -182.7, srl_32->33 -143.7,
    rrl_72->73 -132.6, rrl_25->32 -112.6, srl_25->32 -81.2, rrl_81->82 -80.8.
  - Family D (datapath, inside gate): enc rem_q -40.0 worst (clk), dec u_syn S_q[7] -> bm -15.7 (pma_rck), ~37 small.
- CAUSE (family R) = kit incoherence, not hop budget: kit RTL wrapper = published NF13a/NF15c wrapper (reset tree solved with u_chn at
  1900.8,250.56) but gen.py phys regenerates reset_tree.tcl from the edited plan (planA: u_chn 1548.0,109.44) -> re-solved tree with other
  relay numbering. 129/155 relay flops sat at another relay's site (u_rrl_32 at the rst_o pin x=180; u_rrl_34 = rst_o pin register at
  x=1345 -> 1165-um wire to the port). Proof: scratch rtcheck (RTL .q net per u_[rs]rl_k vs rtr_place key): sd9a kit WRONG 40 by net,
  sd9b kit 0, TP2 hd_tile 0. FAMILY RISK: any kit whose plan copy moves a macro while --kit-rtl keeps the published wrapper.
  Suggested guard: kit_preflight check RTL relay q-net == reset_tree.tcl rtr_place key (fail closed).
- FIX = form sd9c: NF15c (M8 grant 9469b3cd4954b3ea, 1525 tracks) + sd9A u_chn origin 1548.0,109.44 (plan copy
  epyc8 /srv/opentallas-scratch2/claude/head-sd9a/planA15b/prep, only edit), kit RTL = NF15c kit_rtl export (rtl_nf15c, identical to sd9a RTL
  except NF15c clk_landing_ca/meso_fifo), reset_tree.tcl replaced (copy+mv) by the NF15c bootstrap tree (coherent: WRONG 0; 0 sites inside
  the moved u_chn rect); gen copy kept in source_gen_replaced/, record sd9a_reset_tree_source.json. Preflight PASS. Script gen_sd9c.sh.
- LAUNCHED route: kit /srv/opentallas-scratch2/claude/head-sd9a/gen/hd_serdes (replicas epyc7/8/9/10, reset_tree sha 5be86bfb2b5a),
  ot-run picked epyc8, unit oth-ubuntu-4115587-1794884149, client log intel2 ~/head-sd9a-logs/sd9c_route.log, kit log run_route.log.
- NEXT: at GRT read TT list (expect family R gone; D -40 watch), LOOK at grt renders; after DRT signoff gates; export (ffht_export.sh pattern).

## CODEX park on explicit Claude reset — 2026-11-16 19:50 PST
- sd9c inherited route retained unchanged on E8 unit oth-ubuntu-4115587-1794884149, kit /srv/opentallas-scratch2/claude/head-sd9a/gen/hd_serdes, client log ~/head-sd9a-logs/sd9c_route.log. Last read: CTS tap balancing done, 309 delay cells, means396..460ps; no terminal result. NEXT: GRT setup/overflow family read, inspect GRT image; route/signoff/export on passing gates.
- Actual LEC is NOT RUN by async watcher: lec_async.rc0 only means LEC_PREPLACE_DROPPED R-MINIMAL, not equivalence. R371 makes pre/post LEC advisory; no new broad proof launched. No SIGNED claim.
- Place layout LOOKED: three cores clustered in southern logic strip, clear reserved PHY region, no visible overlap; PASS-COND. Record on E8 head-sd9a/results/geom_review/sd9c_place_codex_1116.json. Review record includes explicit LEC correction.
- Source class fix pushed/READY: claude/head-reset-tree-coherence-1116 @b56e08e96e1cd934beacec719ccc81a6dd11cfe3 in existing E10 fable-fix-head-serdes/repo (switched from head-phy-export-source-1116). Tracked files committed, old untracked review files preserved. kit_preflight compares generated reset/start relay placement key with staged top q-net;6 new regression cases. Actual old sd9A60 mismatches; coherent sd9c/TP2 zero. NORMAL GREEN15/15 on main12fbf476346, one core_tap_reach fixture failure also baseline main; record ~/merge-queue/gates/b56e08e96e1cd934beacec719ccc81a6dd11cfe3.json. READY posted; coordinator approval/merge pending. Policy remains R-MINIMAL advisory; no new restrictive gate.
- Latency posted to TOK-VERIFY-3: active sd9c DKREG1/DOREG1 =+2RX/1666ps vs base, 880FF/260.544600um2 per receiver per approved b446902fa18 model. Placement-only change versus sd9A adds0cycles. Existing candidate head1116 contract applies; no final rate/adoption claim. DOreg2+3 fallback is NOT active. If sd9c signs, next HEAD plan must preserve u_chn[1548.0,109.44] and coherent wrapper/reset topology.
- No new jobs launched apart from completed normal source gate. No live kit edits; no new route. All work parked on reset.
