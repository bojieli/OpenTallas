# HBM SU c12 closure (Claude, owner claude-hbm-su) -- updated 2026-10-06 05:20Z
Lanes ADOPTED (main 5b68fde75, results/rtl/hbm_su_c12_20261005/lane_closure.json).
REDUCER TOP CLOSED: red/r7/routes/t7g2_u30p1 (ROGS 2, ff5da4cd1) SS +4.64 / FF +1.51, DRC 0, no slew/cap/fanout viol.
  Slice: red/r7/routes/s7_u30_fp_h25 and red/routes/s2_u30h (hold margin) routing; s5_u30_fp had SS +7.30 / FF -0.58.
CONTROLLER: CTL12=1 N=16 vehicle routed ctl16b_u22 SS -712.6 (2115 pins, ~140 classes). CTL12=2 (working tree, src_ctl2):
  set-up 8/9 sub-steps (4-bit slice products, registered logs/ls/layout/count/L/dR), loop adds/compares kept-prefix on
  registered operands (ssz, nslot, hls0, rem rows, chaining acc + needs), loop/set-up control replicated in 26 kept copies.
  Exact campaign at CTL12=1 and 2: out/campaign_ctl{1,2}.log; vehicle routes routes/ctl16c_u30, _u22, _u26_h20.
-- 2026-10-06 04:55 PT (resumed agent) --
Round 4 vehicle (ctl16f, src_ctl5 = f0a24378a): u22 SS -136.56 (139 pins) / FF +1.8; u26 -127.34 (159) / FF -0.81 (3).
  Classes: g_rt.rt_v[0] (= ret_i) -> n_rtot -> 16b subtract -> inc -> cnt_p1/cnt_e1 (37 pins); ret_i -> n_idseq -> chf -> g_rep u_r (17);
  q_cso -> 5 stride equalities -> s_ni (14).
Round 5 (src_ctl6, working tree on f0a24378a): candidates subtracted from r_tot AND rtot1_r in parallel, ret_i the last select;
  chf per ret_i value uses its own idseq; stride equalities carry-free on the S1 carry-save pair, registered at sub-step 2 (no added cycle).
  Campaigns out/campaign_r6ctl{1,2}.log; routes routes/ctl16g_u{22,26,30}.
-- 07:40 PT: router topk_f3 reassigned to a dedicated agent (handoff /tmp/claude-review-20261003/CLAUDE_HBMSU_TO_ROUTER_AGENT_HANDOFF_20261006.txt; running read-only STA EPYC1 /srv/opentallas-scratch/claude/router-margin/ana)
-- 07:44 PT LOAD-CAP RULE: killed superseded pre-margin controller routes ctl16h_u{22,26,30} (round 6) and ctl16i_u{22,26,30} (round 7 at 833). Kept: ctl16i770_u{22,26} (round 7 routed at 770), red/r7/routes/s8_* (only slice routes), attn routes_q/r3,r4 (EPYC2) + PVE1 routes_q/r1,r2 (margin version). Round-7 GRT at 833: u22 -25.7, u30 -31.0 (ch class only).
-- 07:49 PT ONE-ROUTE RULE: killed ctl16i770_u22/u26 (round 7 @770), ctl16j770_u26 (EPYC2), red/r7 s8_u27_h15 + s8_u33_h12. Kept: controller
   round 8 (src_ctl9: count compares registered one cycle ahead, no added cycle) ctl16j770_u22 on AGIdock /home/ubuntu/claude-hbm-su-ctl/routes
   (routed at 770, sign-off 833 needs >= +40 SS / +15 FF); reducer slice red/r7/routes/s8_u30_h15 (pre-margin, GRT -22.8).
   Campaign r9 (round 8) out/campaign_r9ctl{1,2}.log.
-- 08:25 PT round 8 route ctl16j770_u26 killed at CTS: okA/okE/okH -223..-255 @770 (copy decode -> operand mux -> CSA+adder). Round 9 (src_ctl10):
   compares evaluated for every candidate operand straight from registers, decode only selects 1-bit results; need2 one carry-save add.
   Campaign out/campaign_r10ctl{1,2}.log; the one route routes/ctl16k770_u26 (770 route; sign-off 833 with src_ctl9/physical/hbm_su_c12/signoff_833_fpio.sdc).
-- 09:10 PT round 9 killed (compare path -248 @770). Round 10 = round 7 + reduction-sequence candidate selected last
   (round-7 worst: res_i -> n_irseq -> 8b subtract -> ch, -11.8 @833 CTS); src_ctl11 = round 10 + REDUCER MARGIN (ROPI 1: every
   reducer op registers operands, op ALAT+1; ROUT 2: OUT adds registered). Campaigns out/campaign_r11{c2,c1,neg,rneg}.log
   (neg = OT_NEG_CTL12_CREDIT optimistic credit mutant; rneg = OT_NEG_RED_ROUT2). Round-9 negatives: conservative mutant
   r10neg PASSES (credit is a stall: perf +3 cycles only) -> not a valid control; optimistic mutant r10neg2 FAILS (13 seeds).
   Routes (one per block): controller routes/ctl16l770_u26; reducer margin red/rm/routes/{sm_u30_h15 slice, tm_u30_h15 top}
   (770 route, corner_sta_833.json sign-off). Killed pre-margin s8_u30_h15.
-- 09:59 PT round 10 + reducer margin: exact PASS ctl12 2 / 1 (r11c2 / r11c1); reducer neg (rneg) FAILS; ctl neg2 (optimistic
   credit) FAILS. perf64 first_emit_to_result 285 -> 301 (+16, reducer depth). Reducer TOP margin route tm_u30_h15 GRT +0.36 @770
   (~ +63 @833); slice sm_u30_h15 in floorplan. Controller ctl16l770_u26 GRT -78 @770 on r2_wq (set-up 4x16 slice products, sst 7).
-- 13:50 PT (relaunch after limit) --
Harvest @833.333 sign-off (main corner_sta --post-sdc; the src copies lacked it): controller round 10 ctl16l770_u26 SS +4.16 / FF +1.05
  (one class s_no -> cmul4 -> r2_wq, -59 @770); reducer TOP margin tm_u30_h15 SS +16.36 / FF +7.88 (u_tap tag -> 64 OUT bundles -47 @770,
  pre_v[1] -> 129 hit copies -29 @770). Neither closed. Round-10 negative control (optimistic credit) FAILS: done (060073a87).
Round 11 (dbf7fb9af, src_ctl12): controller slice products as carry-save pairs at sub-step 7, carried at 8, summed at 9 (wnf set-up +1 cycle);
  reducer RKC 1 (kept copies of the hit sources / tap tag, no cycle). Neg controls OT_NEG_CTL12_WQ, OT_NEG_RED_RKC.
  Campaigns out/campaign_r12{c2,c1,nwq,nrkc}.log; routes routes/ctl16m770_u26, red/rm/routes/tm2_u30_h15 (770, corner_sta_833.json).
  Slice sm_u30_h15 (src_redm) still routing.
-- 15:15 PT -- r12 campaigns: c2 PASS, c1 PASS (perf64 first_emit_to_result 301, unchanged); negatives FAIL as required (nwq 27 seeds pass=False, nrkc 40), stopped.
  ctl16m770_u26 (round 11) @833: SS +55.30 (closed) / FF -2.73 (3 pins, u_bt line shift) -> hold-only re-route ctl16m770_u26_h30 on EPYC3 (HM 0.03, buffer cap 100%).
  LOAD REBALANCE: no new EPYC2 launches. CP binder inside the SU block: delegated agent, worktree /home/ubuntu/wt-hbm-su-cpin (EPYC3 scratch hbm-su-cpin).
-- 19:45 PT (relaunch 18:05, new acceptance SS>=+15/FF>=+15 calibrated IO) --
CP-inside-SU ot_hbm_su_cp_side CLOSED SS +79.40 / FF +28.17 (EXEC_OUT=1), view exported, merged main 8bb7532b4 (+9 edges/tx vs +15 standalone).
Re-sign under die IO 0.2T+150 vs vclk at measured insertion (red/io_sta.sh, physical/hbm_su_c12/signoff_833_io150.sdc): top tm2 in -86.9 (v_in->busy OR) / out -214 (false-path route) / FF in -52.8; slice sm FF -57.4; controller ctl16m = SU-lane-internal vehicle, r2r SS +55.3 / FF -2.7.
Round 12 (9916f01b8, src_red13): busy next = v_in | kept b_rest (logically identical; campaign r13c2 PASS, first_emit_to_result 301 unchanged; nrkc running). Routes with calibrated IO (red_route_io.sh, HM 0.03): EPYC2 red/rm/routes/tm3_io_u30 (top, vclk 566), sm3_io_u30 (slice, vclk 831). Controller hold re-route EPYC3 routes/ctl16m770_u26_h30.
-- 23:30 PT -- reducer routes tm3_io_u30 / sm3_io_u30 (EPYC2) still in GRT repair (tm3 -103 @770 on u_lvd lv_in delay line; sm3 -251 @770 on i_x input capture): expect miss -> SAFE PREG (kept pin-stage flops, +4 cycles/reduction). Controller hold re-route ctl16m770_u26_h30 (EPYC3) in GRT (+22 @770 setup). campaign r13c2 PASS, r13nrkc negative FAILS (40 seeds) as required.
