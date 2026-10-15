`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11 r6: hgi_idx_topk_w8_hub -- the GLUE of the 8-wide IDX.TOPK engine as one hard element (owner:
// two-level hierarchy, no intermediate parent): front end (F1 keys, F2 threshold compares), 8 lanes (survivor FIFO 16 x 54,
// credits, extract counters, reverse-buffer SRAM 1024x256 with registered write/read + capture flop, run FIFO, leaf head),
// registered status AND tree, max-root tournament (relay a level), merge tree (relay node on every edge) and the registered
// result skid (ot_hgi_idx_topk_wreg HUB=1).  The 8 hardened heap tiles ot_hgi_topk_heap_tile sit OUTSIDE, one per lane
// pin group t<h>_*; every seam is flop -> wire -> flop (hub output flops / tile pin flops; tile output regs / hub pin flops).
// Defaults = the hardened configuration (a hard child is instantiated without parameter overrides).
// ot_hgi_idx_topk_w8_cluster = hub + 8 heap tiles: the production w8 hard cluster (element hgi_idx_topk_w8; the tiles are
// hard children under OT_TOPK_TILE_HARD, instantiated WITHOUT parameter overrides) and the bench composition (tb -DHUBC).
module ot_hgi_idx_topk_w8_hub #(parameter integer MUT_BYP=0) (
 input wire clk, rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n, cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [255:0] in_score, input wire [3:0] in_nw,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id, out_score, out_row,
 output wire out_last, output wire out_values_valid, output wire done, output wire [3:0] error,
 output wire [11:0] t0_k, output wire t0_op_v, t0_op_ext, t0_clr_go, output wire [53:0] t0_op_x,
 input wire t0_op_cr, t0_ext_v, t0_idle, input wire [53:0] t0_ext_d, input wire [52:0] t0_root_key,
 output wire [11:0] t1_k, output wire t1_op_v, t1_op_ext, t1_clr_go, output wire [53:0] t1_op_x,
 input wire t1_op_cr, t1_ext_v, t1_idle, input wire [53:0] t1_ext_d, input wire [52:0] t1_root_key,
 output wire [11:0] t2_k, output wire t2_op_v, t2_op_ext, t2_clr_go, output wire [53:0] t2_op_x,
 input wire t2_op_cr, t2_ext_v, t2_idle, input wire [53:0] t2_ext_d, input wire [52:0] t2_root_key,
 output wire [11:0] t3_k, output wire t3_op_v, t3_op_ext, t3_clr_go, output wire [53:0] t3_op_x,
 input wire t3_op_cr, t3_ext_v, t3_idle, input wire [53:0] t3_ext_d, input wire [52:0] t3_root_key,
 output wire [11:0] t4_k, output wire t4_op_v, t4_op_ext, t4_clr_go, output wire [53:0] t4_op_x,
 input wire t4_op_cr, t4_ext_v, t4_idle, input wire [53:0] t4_ext_d, input wire [52:0] t4_root_key,
 output wire [11:0] t5_k, output wire t5_op_v, t5_op_ext, t5_clr_go, output wire [53:0] t5_op_x,
 input wire t5_op_cr, t5_ext_v, t5_idle, input wire [53:0] t5_ext_d, input wire [52:0] t5_root_key,
 output wire [11:0] t6_k, output wire t6_op_v, t6_op_ext, t6_clr_go, output wire [53:0] t6_op_x,
 input wire t6_op_cr, t6_ext_v, t6_idle, input wire [53:0] t6_ext_d, input wire [52:0] t6_root_key,
 output wire [11:0] t7_k, output wire t7_op_v, t7_op_ext, t7_clr_go, output wire [53:0] t7_op_x,
 input wire t7_op_cr, t7_ext_v, t7_idle, input wire [53:0] t7_ext_d, input wire [52:0] t7_root_key
);
 wire [95:0] k_w; wire [7:0] v_w, e_w, c_w; wire [431:0] x_w;
 ot_hgi_idx_topk_wreg #(.ENABLE(1'b1), .MAX_K(2048), .IW(8), .W(8), .MUT_BYP(MUT_BYP), .HUB(1'b1)) u (.clk(clk), .rst_n(rst_n),
  .cmd_valid(cmd_valid), .cmd_ready(cmd_ready), .cmd_unit(cmd_unit), .cmd_op(cmd_op), .cmd_param(cmd_param), .cmd_n(cmd_n),
  .cmd_m(cmd_m), .cmd_values(cmd_values), .in_valid(in_valid), .in_ready(in_ready), .in_score(in_score), .in_nw(in_nw),
  .out_valid(out_valid), .out_ready(out_ready), .out_id(out_id), .out_score(out_score), .out_row(out_row),
  .out_last(out_last), .out_values_valid(out_values_valid), .done(done), .error(error),
  .t_k(k_w), .t_op_v(v_w), .t_op_ext(e_w), .t_clr_go(c_w), .t_op_x(x_w),
  .t_op_cr({t7_op_cr, t6_op_cr, t5_op_cr, t4_op_cr, t3_op_cr, t2_op_cr, t1_op_cr, t0_op_cr}),
  .t_ext_v({t7_ext_v, t6_ext_v, t5_ext_v, t4_ext_v, t3_ext_v, t2_ext_v, t1_ext_v, t0_ext_v}),
  .t_idle_i({t7_idle, t6_idle, t5_idle, t4_idle, t3_idle, t2_idle, t1_idle, t0_idle}),
  .t_ext_d({t7_ext_d, t6_ext_d, t5_ext_d, t4_ext_d, t3_ext_d, t2_ext_d, t1_ext_d, t0_ext_d}),
  .t_root_key({t7_root_key, t6_root_key, t5_root_key, t4_root_key, t3_root_key, t2_root_key, t1_root_key, t0_root_key}));
 assign t0_k = k_w[11:0]; assign t0_op_v = v_w[0]; assign t0_op_ext = e_w[0]; assign t0_clr_go = c_w[0]; assign t0_op_x = x_w[53:0];
 assign t1_k = k_w[23:12]; assign t1_op_v = v_w[1]; assign t1_op_ext = e_w[1]; assign t1_clr_go = c_w[1]; assign t1_op_x = x_w[107:54];
 assign t2_k = k_w[35:24]; assign t2_op_v = v_w[2]; assign t2_op_ext = e_w[2]; assign t2_clr_go = c_w[2]; assign t2_op_x = x_w[161:108];
 assign t3_k = k_w[47:36]; assign t3_op_v = v_w[3]; assign t3_op_ext = e_w[3]; assign t3_clr_go = c_w[3]; assign t3_op_x = x_w[215:162];
 assign t4_k = k_w[59:48]; assign t4_op_v = v_w[4]; assign t4_op_ext = e_w[4]; assign t4_clr_go = c_w[4]; assign t4_op_x = x_w[269:216];
 assign t5_k = k_w[71:60]; assign t5_op_v = v_w[5]; assign t5_op_ext = e_w[5]; assign t5_clr_go = c_w[5]; assign t5_op_x = x_w[323:270];
 assign t6_k = k_w[83:72]; assign t6_op_v = v_w[6]; assign t6_op_ext = e_w[6]; assign t6_clr_go = c_w[6]; assign t6_op_x = x_w[377:324];
 assign t7_k = k_w[95:84]; assign t7_op_v = v_w[7]; assign t7_op_ext = e_w[7]; assign t7_clr_go = c_w[7]; assign t7_op_x = x_w[431:378];
endmodule

module ot_hgi_idx_topk_w8_cluster #(parameter integer MUT_BYP=0, parameter integer MUT_CLR=0) (
 input wire clk, rst_n,
 input wire cmd_valid, output wire cmd_ready,
 input wire [3:0] cmd_unit, input wire [5:0] cmd_op,
 input wire [24:0] cmd_param, input wire [31:0] cmd_n, cmd_m,
 input wire cmd_values,
 input wire in_valid, output wire in_ready, input wire [255:0] in_score, input wire [3:0] in_nw,
 output wire out_valid, input wire out_ready,
 output wire [31:0] out_id, out_score, out_row,
 output wire out_last, output wire out_values_valid, output wire done, output wire [3:0] error
);
 // el1011-hbm-idx 2026-10-12 (w8 split): the cluster = boundary FIFOs + the engine glue (ot_hgi_idx_topk_wreg HUB=1 LANE=1:
 // front end, relay stage 0, status AND tree, max-root tournament, per-lane merge credit FIFOs, merge tree, result skid)
 // + 16 HARD children: 8 lane tiles ot_hgi_topk_lane_tile (u_l<h>) and 8 heap tiles ot_hgi_topk_heap_tile (u_t<h>), each
 // lane tile abutting its heap tile.  Hard children are instantiated WITHOUT parameters (bench mutants reach the tiles by
 // define: OT_TOPK_HEAP_MUT_BYP / _CLR / _REV); MUT_BYP / MUT_CLR here are kept for the bench's port list only.
 // el1012-t1 (hold -400 / setup -856 at child rst_n): the rst_n PORT drove 16 hard-child rst_n pins + the boundary FIFOs
 // + the hub across 1.3 mm.  Per the reset design standard (rtl/lib/ot_rst_relay.sv) the port now drives only this
 // relay; region h = lane/heap pair h (placed beside it), 8 = input FIFOs (W edge), 9 = output FIFO + done/error, 10 = hub.
 // All regions release on the same edge (+3 cycles); the hub keeps its own internal relay, so hub-vs-children release
 // order is unchanged.
 wire [10:0] rr;
 // rt_i (Claude group-B4 10-14, rt_h gate in->reg 'rst_n -> u_crr relay RESETN' -251 ps on a 1.3-mm cluster): the port
 // reaches ONE synchroniser at the pin (u_crp); the region relay is cleared from that flop, not from the port.
 wire rp_n;
 ot_rst_relay #(.REGIONS(1), .SYNC_STAGES(2), .TREE_STAGES(1)) u_crp (.clk(clk), .rst_n_in(rst_n), .rst_n(rp_n));
 ot_rst_relay #(.REGIONS(11), .SYNC_STAGES(2), .TREE_STAGES(1)) u_crr (.clk(clk), .rst_n_in(rp_n), .rst_n(rr));
 wire [23:0] l_ph; wire [95:0] l_k; wire [7:0] l_clr, l_pv, l_mcr, l_q, l_x, l_ok, l_mv, l_me;
 wire [431:0] l_pd, l_md; wire [423:0] l_root;
 // r7 (el1011-hbm-idx, w8c df02eb521 textbook lint): REGISTERED cluster boundary.  Every valid/ready port goes through a
 // 2-entry FIFO whose ready is a function of its own count only (no out_ready -> in_ready pass-through), so no port
 // reaches more than one flop and no core path starts or ends at a pin (was out_ready -> b_r 7 levels, in_valid/in_ready
 // registers >= 641-767 um from their pins).  done/error are registered (they follow the registered out stream).
 // rt_j (Claude group-B4 10-14): the engine glue is the hardened HUB TILE ot_hgi_topk_hub_tile (centre channel); the
 // three boundary FIFOs stay at the cluster faces (pin flops at the pins) and talk to the hub over register -> wire ->
 // register links: command valid / registered-ready, scores and results as CREDIT links (no ready crosses the cluster).
 wire hc_v, hc_r, hi_v, hi_cr, ho_v, ho_cr;
 wire [3:0] hc_unit; wire [5:0] hc_op; wire [24:0] hc_param; wire [31:0] hc_n, hc_m; wire hc_values;
 wire [259:0] hi_d; wire [97:0] ho_d;
 ot_hgi_w8_bfifo #(.W(100)) u_bc (.clk(clk), .rst_n(rr[8]), .i_v(cmd_valid), .i_r(cmd_ready),
  .i_d({cmd_unit, cmd_op, cmd_param, cmd_n, cmd_m, cmd_values}), .o_v(hc_v), .o_r(hc_r),
  .o_d({hc_unit, hc_op, hc_param, hc_n, hc_m, hc_values}), .o_cr(1'b0), .i_cr());
 ot_hgi_w8_bfifo #(.W(260), .OCR(6)) u_bi (.clk(clk), .rst_n(rr[8]), .i_v(in_valid), .i_r(in_ready), .i_d({in_score, in_nw}),
  .o_v(hi_v), .o_r(1'b1), .o_d(hi_d), .o_cr(hi_cr), .i_cr());
 ot_hgi_w8_bfifo #(.W(98), .ICR(1), .D(8)) u_bo (.clk(clk), .rst_n(rr[9]), .i_v(ho_v), .i_r(),
  .i_d(ho_d), .o_v(out_valid), .o_r(out_ready),
  .o_d({out_id, out_score, out_row, out_last, out_values_valid}), .o_cr(1'b0), .i_cr(ho_cr));
 ot_hgi_topk_hub_tile #(.NCI(6), .NCO(7), .MUT_BYP(MUT_BYP)) u_hub (.clk(clk), .rst_n(rr[10]),
  .cmd_valid(hc_v), .cmd_ready(hc_r), .cmd_unit(hc_unit), .cmd_op(hc_op), .cmd_param(hc_param), .cmd_n(hc_n), .cmd_m(hc_m),
  .cmd_values(hc_values), .in_v(hi_v), .in_d(hi_d), .in_cr(hi_cr), .out_v(ho_v), .out_d(ho_d), .out_cr(ho_cr),
  .done(done), .error(error),
  .lt_ph_a(l_ph[11:0]), .lt_ph_b(l_ph[23:12]), .lt_k_a(l_k[47:0]), .lt_k_b(l_k[95:48]),
  .lt_clr_a(l_clr[3:0]), .lt_clr_b(l_clr[7:4]), .lt_pv_a(l_pv[3:0]), .lt_pv_b(l_pv[7:4]),
  .lt_mcr_a(l_mcr[3:0]), .lt_mcr_b(l_mcr[7:4]), .lt_pd_a(l_pd[215:0]), .lt_pd_b(l_pd[431:216]),
  .lt_q_a(l_q[3:0]), .lt_q_b(l_q[7:4]), .lt_x_a(l_x[3:0]), .lt_x_b(l_x[7:4]), .lt_ok_a(l_ok[3:0]), .lt_ok_b(l_ok[7:4]),
  .lt_mv_a(l_mv[3:0]), .lt_mv_b(l_mv[7:4]), .lt_me_a(l_me[3:0]), .lt_me_b(l_me[7:4]),
  .lt_root_a(l_root[211:0]), .lt_root_b(l_root[423:212]), .lt_md_a(l_md[215:0]), .lt_md_b(l_md[431:216]));
 wire [11:0] k0; wire v0, e0, c0, cr0, xv0, id0; wire [53:0] x0, xd0; wire [52:0] rk0;
 ot_hgi_topk_lane_tile u_l0 (.clk(clk), .rst_n(rr[0]), .ph(l_ph[2:0]), .kin(l_k[11:0]), .clr(l_clr[0]),
  .pv(l_pv[0]), .pd(l_pd[53:0]), .mcr(l_mcr[0]), .q(l_q[0]), .x(l_x[0]), .ok(l_ok[0]),
  .root(l_root[52:0]), .mv(l_mv[0]), .md(l_md[53:0]), .me(l_me[0]),
  .t_k(k0), .t_op_v(v0), .t_op_ext(e0), .t_clr_go(c0), .t_op_x(x0), .t_op_cr(cr0), .t_ext_v(xv0), .t_idle(id0),
  .t_ext_d(xd0), .t_root_key(rk0));
 ot_hgi_topk_heap_tile u_t0 (.clk(clk), .rst_n(rr[0]), .k(k0), .op_v(v0), .op_ext(e0), .op_x(x0), .op_cr(cr0),
  .ext_v(xv0), .ext_d(xd0), .root_key(rk0), .clr_go(c0), .idle(id0));
 wire [11:0] k1; wire v1, e1, c1, cr1, xv1, id1; wire [53:0] x1, xd1; wire [52:0] rk1;
 ot_hgi_topk_lane_tile u_l1 (.clk(clk), .rst_n(rr[1]), .ph(l_ph[5:3]), .kin(l_k[23:12]), .clr(l_clr[1]),
  .pv(l_pv[1]), .pd(l_pd[107:54]), .mcr(l_mcr[1]), .q(l_q[1]), .x(l_x[1]), .ok(l_ok[1]),
  .root(l_root[105:53]), .mv(l_mv[1]), .md(l_md[107:54]), .me(l_me[1]),
  .t_k(k1), .t_op_v(v1), .t_op_ext(e1), .t_clr_go(c1), .t_op_x(x1), .t_op_cr(cr1), .t_ext_v(xv1), .t_idle(id1),
  .t_ext_d(xd1), .t_root_key(rk1));
 ot_hgi_topk_heap_tile u_t1 (.clk(clk), .rst_n(rr[1]), .k(k1), .op_v(v1), .op_ext(e1), .op_x(x1), .op_cr(cr1),
  .ext_v(xv1), .ext_d(xd1), .root_key(rk1), .clr_go(c1), .idle(id1));
 wire [11:0] k2; wire v2, e2, c2, cr2, xv2, id2; wire [53:0] x2, xd2; wire [52:0] rk2;
 ot_hgi_topk_lane_tile u_l2 (.clk(clk), .rst_n(rr[2]), .ph(l_ph[8:6]), .kin(l_k[35:24]), .clr(l_clr[2]),
  .pv(l_pv[2]), .pd(l_pd[161:108]), .mcr(l_mcr[2]), .q(l_q[2]), .x(l_x[2]), .ok(l_ok[2]),
  .root(l_root[158:106]), .mv(l_mv[2]), .md(l_md[161:108]), .me(l_me[2]),
  .t_k(k2), .t_op_v(v2), .t_op_ext(e2), .t_clr_go(c2), .t_op_x(x2), .t_op_cr(cr2), .t_ext_v(xv2), .t_idle(id2),
  .t_ext_d(xd2), .t_root_key(rk2));
 ot_hgi_topk_heap_tile u_t2 (.clk(clk), .rst_n(rr[2]), .k(k2), .op_v(v2), .op_ext(e2), .op_x(x2), .op_cr(cr2),
  .ext_v(xv2), .ext_d(xd2), .root_key(rk2), .clr_go(c2), .idle(id2));
 wire [11:0] k3; wire v3, e3, c3, cr3, xv3, id3; wire [53:0] x3, xd3; wire [52:0] rk3;
 ot_hgi_topk_lane_tile u_l3 (.clk(clk), .rst_n(rr[3]), .ph(l_ph[11:9]), .kin(l_k[47:36]), .clr(l_clr[3]),
  .pv(l_pv[3]), .pd(l_pd[215:162]), .mcr(l_mcr[3]), .q(l_q[3]), .x(l_x[3]), .ok(l_ok[3]),
  .root(l_root[211:159]), .mv(l_mv[3]), .md(l_md[215:162]), .me(l_me[3]),
  .t_k(k3), .t_op_v(v3), .t_op_ext(e3), .t_clr_go(c3), .t_op_x(x3), .t_op_cr(cr3), .t_ext_v(xv3), .t_idle(id3),
  .t_ext_d(xd3), .t_root_key(rk3));
 ot_hgi_topk_heap_tile u_t3 (.clk(clk), .rst_n(rr[3]), .k(k3), .op_v(v3), .op_ext(e3), .op_x(x3), .op_cr(cr3),
  .ext_v(xv3), .ext_d(xd3), .root_key(rk3), .clr_go(c3), .idle(id3));
 wire [11:0] k4; wire v4, e4, c4, cr4, xv4, id4; wire [53:0] x4, xd4; wire [52:0] rk4;
 ot_hgi_topk_lane_tile u_l4 (.clk(clk), .rst_n(rr[4]), .ph(l_ph[14:12]), .kin(l_k[59:48]), .clr(l_clr[4]),
  .pv(l_pv[4]), .pd(l_pd[269:216]), .mcr(l_mcr[4]), .q(l_q[4]), .x(l_x[4]), .ok(l_ok[4]),
  .root(l_root[264:212]), .mv(l_mv[4]), .md(l_md[269:216]), .me(l_me[4]),
  .t_k(k4), .t_op_v(v4), .t_op_ext(e4), .t_clr_go(c4), .t_op_x(x4), .t_op_cr(cr4), .t_ext_v(xv4), .t_idle(id4),
  .t_ext_d(xd4), .t_root_key(rk4));
 ot_hgi_topk_heap_tile u_t4 (.clk(clk), .rst_n(rr[4]), .k(k4), .op_v(v4), .op_ext(e4), .op_x(x4), .op_cr(cr4),
  .ext_v(xv4), .ext_d(xd4), .root_key(rk4), .clr_go(c4), .idle(id4));
 wire [11:0] k5; wire v5, e5, c5, cr5, xv5, id5; wire [53:0] x5, xd5; wire [52:0] rk5;
 ot_hgi_topk_lane_tile u_l5 (.clk(clk), .rst_n(rr[5]), .ph(l_ph[17:15]), .kin(l_k[71:60]), .clr(l_clr[5]),
  .pv(l_pv[5]), .pd(l_pd[323:270]), .mcr(l_mcr[5]), .q(l_q[5]), .x(l_x[5]), .ok(l_ok[5]),
  .root(l_root[317:265]), .mv(l_mv[5]), .md(l_md[323:270]), .me(l_me[5]),
  .t_k(k5), .t_op_v(v5), .t_op_ext(e5), .t_clr_go(c5), .t_op_x(x5), .t_op_cr(cr5), .t_ext_v(xv5), .t_idle(id5),
  .t_ext_d(xd5), .t_root_key(rk5));
 ot_hgi_topk_heap_tile u_t5 (.clk(clk), .rst_n(rr[5]), .k(k5), .op_v(v5), .op_ext(e5), .op_x(x5), .op_cr(cr5),
  .ext_v(xv5), .ext_d(xd5), .root_key(rk5), .clr_go(c5), .idle(id5));
 wire [11:0] k6; wire v6, e6, c6, cr6, xv6, id6; wire [53:0] x6, xd6; wire [52:0] rk6;
 ot_hgi_topk_lane_tile u_l6 (.clk(clk), .rst_n(rr[6]), .ph(l_ph[20:18]), .kin(l_k[83:72]), .clr(l_clr[6]),
  .pv(l_pv[6]), .pd(l_pd[377:324]), .mcr(l_mcr[6]), .q(l_q[6]), .x(l_x[6]), .ok(l_ok[6]),
  .root(l_root[370:318]), .mv(l_mv[6]), .md(l_md[377:324]), .me(l_me[6]),
  .t_k(k6), .t_op_v(v6), .t_op_ext(e6), .t_clr_go(c6), .t_op_x(x6), .t_op_cr(cr6), .t_ext_v(xv6), .t_idle(id6),
  .t_ext_d(xd6), .t_root_key(rk6));
 ot_hgi_topk_heap_tile u_t6 (.clk(clk), .rst_n(rr[6]), .k(k6), .op_v(v6), .op_ext(e6), .op_x(x6), .op_cr(cr6),
  .ext_v(xv6), .ext_d(xd6), .root_key(rk6), .clr_go(c6), .idle(id6));
 wire [11:0] k7; wire v7, e7, c7, cr7, xv7, id7; wire [53:0] x7, xd7; wire [52:0] rk7;
 ot_hgi_topk_lane_tile u_l7 (.clk(clk), .rst_n(rr[7]), .ph(l_ph[23:21]), .kin(l_k[95:84]), .clr(l_clr[7]),
  .pv(l_pv[7]), .pd(l_pd[431:378]), .mcr(l_mcr[7]), .q(l_q[7]), .x(l_x[7]), .ok(l_ok[7]),
  .root(l_root[423:371]), .mv(l_mv[7]), .md(l_md[431:378]), .me(l_me[7]),
  .t_k(k7), .t_op_v(v7), .t_op_ext(e7), .t_clr_go(c7), .t_op_x(x7), .t_op_cr(cr7), .t_ext_v(xv7), .t_idle(id7),
  .t_ext_d(xd7), .t_root_key(rk7));
 ot_hgi_topk_heap_tile u_t7 (.clk(clk), .rst_n(rr[7]), .k(k7), .op_v(v7), .op_ext(e7), .op_x(x7), .op_cr(cr7),
  .ext_v(xv7), .ext_d(xd7), .root_key(rk7), .clr_go(c7), .idle(id7));
endmodule

// Four-entry elastic boundary FIFO with a dedicated single-capture input stage.
// The pending input beat counts against capacity, so registered ingress never
// overwrites an entry during a downstream stall. Sustained service stays one
// beat/cycle; the input register adds one edge compared with the two-bank FIFO.
module ot_hgi_w8_bfifo #(parameter integer W=32, parameter integer RIR=0,
 // rt_j credit modes (hub tile links): OCR=N: the output side is a CREDIT link (N credits; o_v = a beat sent this edge,
 // no o_r; o_cr returns one credit).  ICR=1: the input side is a credit link (every i_v beat is taken, i_cr returns one
 // credit per beat delivered at o_v && o_r); i_r is then constant 1 and unused.
 parameter integer OCR=0, parameter integer ICR=0,
 parameter integer D=4) (                            // entries (power of two; rt_j: the E-face result FIFO holds 8)
 input wire clk, rst_n,
 input wire i_v, output wire i_r, input wire [W-1:0] i_d,
 output wire o_v, input wire o_r, output wire [W-1:0] o_d,
 input wire o_cr, output reg i_cr
);
 reg [W-1:0] pin_d;
 reg [W-1:0] head_d;
 reg pin_v, up;
 localparam integer DA = $clog2(D);
 reg [W-1:0] mem [0:D-1];
 reg [DA-1:0] wp, rp;
 reg [DA:0] cnt;
 wire push = (ICR != 0) ? i_v : (i_v && i_r);
 wire pop;
 wire [DA+1:0] occupied = {1'b0, cnt} + (DA+2)'(pin_v);
 // rt_i RIR=1 (rt_h gate 'u_bo.pin_v -> u_hub.active / c_valid / b_r' -67..-38 ps): i_r is a REGISTER holding the same
 // value (up && cnt + pin_v < 4 of this edge), loaded from the next state; the o_r pin only picks between the two
 // registered-state candidates (pop / no pop).
 generate if (ICR != 0) begin : g_icr
  assign i_r = 1'b1;
 end else if (RIR != 0) begin : g_rir
  reg ir_q;
  wire [DA+1:0] occ_np = {1'b0, cnt} + (DA+2)'(pin_v) + (DA+2)'(push);     // next cnt + next pin_v without a pop
  wire ir_np = occ_np < D, ir_p = occ_np - 1'b1 < D;
  always @(posedge clk or negedge rst_n) if (!rst_n) ir_q <= 1'b0; else ir_q <= pop ? ir_p : ir_np;
  assign i_r = ir_q;
 end else begin : g_cir
  assign i_r = up && occupied < D;
 end endgenerate
 localparam integer CRW = (OCR > 0) ? $clog2(OCR + 1) : 1;
 reg [CRW-1:0] ocr;
 generate if (OCR != 0) begin : g_ocr
  assign o_v = cnt != 0 && ocr != 0;                  // a beat is SENT this edge (the receiver always takes it)
  assign pop = o_v;
 end else begin : g_ov
  assign o_v = cnt != 0;
  assign pop = o_v && o_r;
 end endgenerate
 assign o_d = head_d;
`ifdef OT_TOPK_FIFO_HEAD_MUT
 wire [DA-1:0] next_rp = (W == 98) ? rp : rp + 1'b1; // stale output head; command/ingress protocol unchanged
`else
 wire [DA-1:0] next_rp = rp + 1'b1;
`endif
 (* keep *) wire [W-1:0] h_pop = (cnt > 1) ? mem[next_rp] : (pin_v ? pin_d : head_d);
 (* keep *) wire [W-1:0] h_hold = (cnt == 0 && pin_v) ? pin_d : head_d;
 // Input pins each reach exactly one reset-free capture flop. The valid bit
 // carries the acceptance event; invalid input samples are never consumed.
 always @(posedge clk) begin
  pin_d <= i_d;
  if (pin_v) mem[wp] <= pin_d;
  // Cache the oldest entry: no memory-selection cone remains after the
  // output launch flop. Bypass the incoming beat at empty/last-pop boundaries.
  // B2 (Claude hbm-group-B r2 10-14, rt_g TT class 'out_ready -> u_bo head_d 13 levels'): both candidate next heads
  // (h_pop: the head if this edge pops, h_hold: if it does not) come from registered state only (cnt, rp, mem, pin_v,
  // pin_d, head_d); the raw o_r pin only selects between them, one kept 2:1 mux per bit.  The same value on every edge
  // as the nested form (a pop implies cnt != 0, so the empty bypass belongs to h_hold only).
  head_d <= pop ? h_pop : h_hold;
 end
 always @(posedge clk or negedge rst_n)
  if (!rst_n) begin wp <= 0; rp <= 0; up <= 0; pin_v <= 0; cnt <= 0; ocr <= CRW'(OCR); i_cr <= 1'b0; end
  else begin
   if (OCR != 0) ocr <= ocr - CRW'(pop) + CRW'(o_cr);
   i_cr <= (ICR != 0) && pop;
   up <= 1;
   pin_v <= push;
   if (pin_v) wp <= wp + 1'b1;
   if (pop) rp <= rp + 1'b1;
   cnt <= cnt + (DA+1)'(pin_v) - (DA+1)'(pop);
  end
endmodule
