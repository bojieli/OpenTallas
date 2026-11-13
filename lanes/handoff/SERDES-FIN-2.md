# SERDES-FIN-2 handoff (Opus successor of HARD-S81-SERDES-1; COORD is the coordinator)

Read lanes/handoff/HARD-S81-SERDES-1.md first (design, proofs, kit layout).

## State 2026-11-13 07:01 PST
- Branch claude/hard-s81-serdes-1-1113 PUSHED to hub at 01197b5d5d (4 commits off fbfb4fc6a6). Worktree epyc9 /srv/opentallas-scratch2/claude/hard-s81-serdes-1/wt.
- kitA (island at today site, density 0.65) place DONE 06:59: dp TT wns -1101 tns -3.33e6; render: island logic still smeared along the S band; worst = u_face_p_d -> u_syn.am_ok (5 FA + 20 cells, 100-333 ps wire between cells). LEC async OOM-killed (exit 137): needs fresh LEC. STA bucket sta_kitA_v2 running (ot-run).
- kitB (template v3) placing (detail place), kitS3 (seqhost LA v3) placing (resize). Waiters in my shell.

## 2026-11-13 07:13 collect
- kitB (template v3) place DONE: TT wns -3595 tns -12.3M (STA sta_kitB). Render: island compact under PMA E end, lane rows on the SE diagonal to the pin strip = the intended template picture (local density 0.90). Classes: u_rm rp_g2 -> mem we 4091 ep -3595 (R-RTL-2, 4096-load push); u_syn S_q/ldr 2.6k ep -1300 (R-RTL-2 syndrome broadcast); rm rp 444 -222; enc rem_q 280 -244; lpin 8 -472.
- kitA (today site) STA: wns -932, same classes (rp_g2 4094 ep -856, lpl rq 1636 -330).
- PICK: template form (kitB geometry) + the existing vB/vJ cone defines (proven 11-07/11-09 by S81-RCK-10 / DIE-S81-85): OT_S81_SERDES_RST_TREE RM_STAGED RM_LOCAL4 RM_WFULL8 KP4_SYN_LOCAL KP4_AM_FACE3 CLAND_WCHK (RCK_RELAY4 not used: LANE_RXI replaces it). = kitC, synth+place launched (log kitC_place). Neither A nor B goes to CTS as-is (cones, not geometry).
- bench6vb: LANE 3/4/5/3 lock-step ON TOP of the vB define set (run_serdes_lane_bench.sh EXTRA_DEFS, new) running.
- kitS3 seqhost place: TT wns -284 (STA -247), 3863 ep; 2983 ep from u_win.armed (-115, R-RTL-2: armed -> ss -> rec -> 47x63 table write enables); vld 125 -110; cq_rd -146; ttg rd_out -146 (host engine, not hwin). STA -from armed running.

## 2026-11-13 07:26 HANDBACK state (COORD: Fable reset, scope returns to HARD-S81-SERDES-1)
BRANCH: claude/hard-s81-serdes-1-1113 PUSHED to hub, tip a364834a2c (verified ls-remote). Commits added by me on top of 01197b5d5d:
- 330afa2a88 seqhost dsdv_mu_hwin LA 4 (define OT_S81_SH_WIN_SS): ss / one-hot / on_cal registered from next-state armed/sl/ph, every table write enabled per slot (R-RTL-2, 0 cycles); run_serdes_lane_bench.sh EXTRA_DEFS; bench records hwin6_* and bench6vb_*.
- a364834a2c serdes_template.py: apply adds the 7 cone defines (CONE_DEFINES; --no-cone = LANE only), moves the SRAMs that are physical_parts of u_phy (the old apply moved only u_chn on the real plan), --delta; tests 11 pass. Delta vs origin main plan_h2_2249.json (sha256 e596e9588e72, main 5eefdbe2fa): results/hard_s81_serdes_1_1113/delta/serdes_fin_delta.json, 11 types x 3 moves + serdes_lanes + defines. NOT adopted (freeze to 11-15 04:00); no READY posted yet.

RESULTS (lane dir epyc9 /srv/opentallas-scratch2/claude/hard-s81-serdes-1, logs intel2 ~/hard-s81-serdes-1-logs):
- t2 kitA (today site, LANE only): dp TT wns -1101; STA sta_kitA_v2 wns -932, 6739 ep: u_rm rp_g2 -> mem write enable 4094 ep -856; lpl_5_w rq 1636 -330; rm rp 511 -625. LEC OOM-killed (exit 137): kit needs a fresh LEC.
- t2 kitB (template v3, LANE only): dp wns -3941; STA sta_kitB wns -3595, 7736 ep: rp_g2 push (15 cells + 4096-load enable) 4091 -3595; u_syn S_q / ldr 2.8k ep -1300; rm rp 444 -222; enc rem_q 280 -244; lpin 8 -472. Render GOOD geometry (compact island under PMA E end, lane rows on the SE diagonal, local density 0.90). Verdict: geometry is the template F5 asked for; the failures are R-RTL-2 cones, not reach. Neither A nor B goes to CTS as-is.
- PICK = template (kitB geometry) + the already-proven cone defines (S81-RCK-10 vJ / DIE-S81-85 vB): RST_TREE RM_STAGED RM_LOCAL4 RM_WFULL8 KP4_SYN_LOCAL KP4_AM_FACE3 CLAND_WCHK (no RCK_RELAY4: LANE_RXI replaces it).
- bench6vb (LANE 3/4/5/3 OVER that cone set): lane PASS (tx 9247/0 bad, rck 9299/0, RX 6000 seq_diff 0); mut8/9/10, xtx, xrx all FAIL as required; loopback vB-only 95, +LANE 110 (released 88: +22 clk total; the latency_rows.json in the branch still lists LANE only (+15) and must get the vB rows: rate match +2 wclk/+3 rclk, SYN_LOCAL +2 rck, RST_TREE +1 clk reset edge).
- seqhost kitS3 (LA 1): dp wns -284; STA sta_kitS3 wns -247, 3863 ep: u_win.armed 2983 ep -115 (armed -> ss mux -> on_cal/col -> rec -> 64x63 table enables, 13 cells + 12 buffers); vld 125 -110; eng cq_rd 51 -146; l2 ttg rd_out 38 -146; pe_tb 10 -247. LA 4 written for the armed class.
- hwin6 (LA 4 vs LA 0 lock-step): PASS NS 47 (seeds 11, 12), 64, 12, 4; LA 1 PASS; mutant LA 5 FAIL at NS 47 and 12.

IN FLIGHT (do not cancel; mine):
- kitC = kitB + cone defines, ot-run synth -> place (log kitC_place.otrun.log; kit epyc9 .../kitC/gen/serdes__t2). At 15:3x it was in synth.
- kitS4 = kitS3 + OT_S81_SH_WIN_SS (rtl/dsdv_mu_hwin.sv copied from the branch), ot-run synth -> place (log kitS4_place.otrun.log).
- Old LEC containers still running on epyc9 for superseded kits (dpkit-seqhost__t1-1078337-lec kitS, -2206801-lec kitS2): not touched.

NEXT (for HARD-S81-SERDES-1):
1. kitC place: view density.png; STA bucket (sta_run.sh + sta_bucket.py). If the cone classes are gone: resume.json {"start":"cts", note new text} and run_kit.sh route. rck: a27 CTS gave io_pma_rck 22,306 sinks, insertion 2.0-2.5 ns, skew 467 ps (sinks 3.5 mm apart); with the island they are inside ~760x304 um: check 4_1_cts.log tree for io_pma_rck[0]_regs (levels, skew) and give it a root buffer at the island centre if TritonCTS starts at the far port.
2. kitS4 place: STA; remaining non-hwin classes (eng cq_rd, l2 ttg rd_out, hi f_code) are host-engine RTL; then CTS/route to sign-off.
3. READY branches off origin main (>= 24b08535da; main now 5eefdbe2fa): (a) RTL: col LANE + tb + bench script, hwin LA/LA4 + tb, latency rows (add the vB rows); (b) tools: serdes_lanes.tcl/release, gen_phys/schema key, serdes_template.py + tests; (c) plan delta results/hard_s81_serdes_1_1113/delta (adopt after 11-15 04:00; re-run serdes_template.py --delta on the then-current plan).
4. RULEBOOK R-RTL: the S81 serdes row should now name the measured KP4 / RM cones (rp_g2 push 15 cells + 4096 loads; syndrome S_q/ldr 2.8k ep) and their fix (vB set); seqhost row: measured (armed 2983 ep -115, R-RTL-2) -> LA 4. Not edited by me.

HANDBACK 2026-11-13 07:26 to HARD-S81-SERDES-1
