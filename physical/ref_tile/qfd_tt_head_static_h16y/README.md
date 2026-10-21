# qfd_tt_head_static_h16y -- h16x successor (QW-H16Y 10-21), TOK.QW.LAYER.3.SEG head leaf: round 3

h16x route (qfd_tt_head_static_h16x-h16x-afc3367a6, NEEDS_RTL TT -227.86 / FF +6.08; h16xb pd 0.7 TT -230.86) re-timed
on 6_final.odb + SPEF with signoff.sdc (164 violating endpoints, grouped by RTL register):
- macro->reg -190.8 (108): program SRAM rd_out -> p_cap.  The h16x raw capture has no logic (early issue took effect), but
  the program stores sat MY: rd_out pins are on LEF x=0, so they faced EAST while p_cap/prog_q/FIFO sit WEST; each bit ran
  3 x BUFx16 + ~480 ps of wire (443 ps slew).  Macro clk slew 265 ps, clk->q 424 ps, macro clock +50 ps late.
- reg->reg -227.9 (47): calendar q <- g_base / sealed: 12-b start compare -> start_cal -> sel_g / read-enable fan-out over a
  ~250 ps rebuffered wire -> 10-level row mux.  q -> issue fault -153.6, pending_index -> sched_q -104, rows -> cfg_fault
  -95.7 / sealed -57 / loading -40: the fixed-issue flops were spread over x 166-320 / y 39-291 um (12% std-cell density).

RTL (H16X = 2 on ot_qfd_tt_ctlm_static_hr_safe32; claude/qw-h16y-1021; all exact, 0 edges):
- start_base==0 and start_base==g_base registered one edge early from prog_base (start_base_pre; start_base = prog_base
  through u_isd, IS 1); g_base next state = this edge's GDESC write.  Sim check: equals the as-built compares every edge.
- calendar read register q loaded EVERY edge with a late start/run select (start: row 0 of segment !sb_z; run: seg_q at
  second_read ? 1 : index+2); q is read by u_issue only when pending (= a read on the previous edge).  Sim check: q equals
  the as-built enabled read register whenever pending; read_fault keeps the read-enable gate.
- issue fault split into sticky halves fault_c | fault_s (slot_q / next-row checks), both cleared on start.
RTL parent (qfd_tt_ctlm_dv + safe32 head H16X=2, all $fatal reference checks) V5.050 ep7: img0 PASS 123/123, imgh PASS
131/131 (results/rtl/qw_head_safe32_1020/h16y/run_rtl_parent.sh).
Netlist: results/rtl/qw_head_safe32_1020/h16y/run_gen.sh (h16x chain/ABC, -chparam H16X 2): 25,383 cells, 7,175 flops,
max depth 21 (cfg_fault <- rows, 1 flop), 0 over 30; calendar q no longer in the depth top list.

## SAFE-DESIGN checklist
1 Pins: pin registers ON (ck_head); reset landed by the kit (2 stages) -- PASS (as h16x)
2 Reach: 345.6 x 302.4 leaf; program rd_out now 35 um to the FIFO column (was ~200 um) -- FIXED
3 Fanout: bounded netlist load-cap 16 (32 input / reset) -- PASS by construction; gate native census (limit 32)
4 Depth: max 21 levels (1 flop); calendar start compare pre-registered, q late select, fault split -- FIXED (gate)
5 Storage: unchanged (FIFO 6x 32x128 SRAM + 2x 64x512 program store); new regs sbz_r/sbg_r/fault_s 3 b -- PASS
6 Floorplan: h16x geometry (8 macros on the 43.2 lattice) with the two 64x512 program stores turned R0 so their rd_out face (LEF x=0) faces the FIFO column 35 um west (h16x MY: 1024 rd_out bits crossed ~200 um east->west, -190.8 ps); fixed-issue flops fenced x 140-295 / y 128-167 (155 x 39 um channel between the program stores beside the E-face pw/prog_base pins), released before DPL -- FIXED; E face pin-bound (unchanged) WARN
7 Clock: single CTS root ck_head (flops + 8 SRAM clock pins), no crossing -- gate
8 Schedule: 0 added edges (all cuts register exact next values / consumer-equivalent loads) -- PASS; nothing to price
