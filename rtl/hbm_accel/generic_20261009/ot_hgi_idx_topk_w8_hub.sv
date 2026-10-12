`timescale 1ns/1ps
// el1011-hbm-idx 2026-10-11 r6: hgi_idx_topk_w8_hub -- the GLUE of the 8-wide IDX.TOPK engine as one hard element (owner:
// two-level hierarchy, no intermediate parent): front end (F1 keys, F2 threshold compares), 8 lanes (survivor FIFO 16 x 54,
// credits, extract counters, reverse-buffer SRAM 1024x256 with registered write/read + capture flop, run FIFO, leaf head),
// registered status AND tree, max-root tournament (relay a level), merge tree (relay node on every edge) and the registered
// result skid (ot_hgi_idx_topk_wreg HUB=1).  The 8 hardened heap tiles ot_hgi_topk_heap_tile sit OUTSIDE, one per lane
// pin group t<h>_*; every seam is flop -> wire -> flop (hub output flops / tile pin flops; tile output regs / hub pin flops).
// Defaults = the hardened configuration (a hard child is instantiated without parameter overrides).
// ot_hgi_idx_topk_w8_comp = hub + 8 RTL tiles: the bench composition (tb -DHUBC).
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

`ifndef OT_TOPK_TILE_HARD
module ot_hgi_idx_topk_w8_comp #(parameter integer MUT_BYP=0, parameter integer MUT_CLR=0) (
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
 wire [11:0] k0; wire v0, e0, c0, cr0, xv0, id0; wire [53:0] x0, xd0; wire [52:0] rk0;
 wire [11:0] k1; wire v1, e1, c1, cr1, xv1, id1; wire [53:0] x1, xd1; wire [52:0] rk1;
 wire [11:0] k2; wire v2, e2, c2, cr2, xv2, id2; wire [53:0] x2, xd2; wire [52:0] rk2;
 wire [11:0] k3; wire v3, e3, c3, cr3, xv3, id3; wire [53:0] x3, xd3; wire [52:0] rk3;
 wire [11:0] k4; wire v4, e4, c4, cr4, xv4, id4; wire [53:0] x4, xd4; wire [52:0] rk4;
 wire [11:0] k5; wire v5, e5, c5, cr5, xv5, id5; wire [53:0] x5, xd5; wire [52:0] rk5;
 wire [11:0] k6; wire v6, e6, c6, cr6, xv6, id6; wire [53:0] x6, xd6; wire [52:0] rk6;
 wire [11:0] k7; wire v7, e7, c7, cr7, xv7, id7; wire [53:0] x7, xd7; wire [52:0] rk7;
 ot_hgi_idx_topk_w8_hub #(.MUT_BYP(0)) u_hub (.clk(clk), .rst_n(rst_n), .cmd_valid(cmd_valid), .cmd_ready(cmd_ready),
  .cmd_unit(cmd_unit), .cmd_op(cmd_op), .cmd_param(cmd_param), .cmd_n(cmd_n), .cmd_m(cmd_m), .cmd_values(cmd_values),
  .in_valid(in_valid), .in_ready(in_ready), .in_score(in_score), .in_nw(in_nw), .out_valid(out_valid), .out_ready(out_ready),
  .out_id(out_id), .out_score(out_score), .out_row(out_row), .out_last(out_last), .out_values_valid(out_values_valid),
  .done(done), .error(error),
  .t0_k(k0), .t0_op_v(v0), .t0_op_ext(e0), .t0_clr_go(c0), .t0_op_x(x0), .t0_op_cr(cr0), .t0_ext_v(xv0),
  .t0_idle(id0), .t0_ext_d(xd0), .t0_root_key(rk0),
  .t1_k(k1), .t1_op_v(v1), .t1_op_ext(e1), .t1_clr_go(c1), .t1_op_x(x1), .t1_op_cr(cr1), .t1_ext_v(xv1),
  .t1_idle(id1), .t1_ext_d(xd1), .t1_root_key(rk1),
  .t2_k(k2), .t2_op_v(v2), .t2_op_ext(e2), .t2_clr_go(c2), .t2_op_x(x2), .t2_op_cr(cr2), .t2_ext_v(xv2),
  .t2_idle(id2), .t2_ext_d(xd2), .t2_root_key(rk2),
  .t3_k(k3), .t3_op_v(v3), .t3_op_ext(e3), .t3_clr_go(c3), .t3_op_x(x3), .t3_op_cr(cr3), .t3_ext_v(xv3),
  .t3_idle(id3), .t3_ext_d(xd3), .t3_root_key(rk3),
  .t4_k(k4), .t4_op_v(v4), .t4_op_ext(e4), .t4_clr_go(c4), .t4_op_x(x4), .t4_op_cr(cr4), .t4_ext_v(xv4),
  .t4_idle(id4), .t4_ext_d(xd4), .t4_root_key(rk4),
  .t5_k(k5), .t5_op_v(v5), .t5_op_ext(e5), .t5_clr_go(c5), .t5_op_x(x5), .t5_op_cr(cr5), .t5_ext_v(xv5),
  .t5_idle(id5), .t5_ext_d(xd5), .t5_root_key(rk5),
  .t6_k(k6), .t6_op_v(v6), .t6_op_ext(e6), .t6_clr_go(c6), .t6_op_x(x6), .t6_op_cr(cr6), .t6_ext_v(xv6),
  .t6_idle(id6), .t6_ext_d(xd6), .t6_root_key(rk6),
  .t7_k(k7), .t7_op_v(v7), .t7_op_ext(e7), .t7_clr_go(c7), .t7_op_x(x7), .t7_op_cr(cr7), .t7_ext_v(xv7),
  .t7_idle(id7), .t7_ext_d(xd7), .t7_root_key(rk7));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t0 (.clk(clk), .rst_n(rst_n), .k(k0),
  .op_v(v0), .op_ext(e0), .op_x(x0), .op_cr(cr0), .ext_v(xv0), .ext_d(xd0), .root_key(rk0), .clr_go(c0), .idle(id0));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t1 (.clk(clk), .rst_n(rst_n), .k(k1),
  .op_v(v1), .op_ext(e1), .op_x(x1), .op_cr(cr1), .ext_v(xv1), .ext_d(xd1), .root_key(rk1), .clr_go(c1), .idle(id1));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t2 (.clk(clk), .rst_n(rst_n), .k(k2),
  .op_v(v2), .op_ext(e2), .op_x(x2), .op_cr(cr2), .ext_v(xv2), .ext_d(xd2), .root_key(rk2), .clr_go(c2), .idle(id2));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t3 (.clk(clk), .rst_n(rst_n), .k(k3),
  .op_v(v3), .op_ext(e3), .op_x(x3), .op_cr(cr3), .ext_v(xv3), .ext_d(xd3), .root_key(rk3), .clr_go(c3), .idle(id3));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t4 (.clk(clk), .rst_n(rst_n), .k(k4),
  .op_v(v4), .op_ext(e4), .op_x(x4), .op_cr(cr4), .ext_v(xv4), .ext_d(xd4), .root_key(rk4), .clr_go(c4), .idle(id4));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t5 (.clk(clk), .rst_n(rst_n), .k(k5),
  .op_v(v5), .op_ext(e5), .op_x(x5), .op_cr(cr5), .ext_v(xv5), .ext_d(xd5), .root_key(rk5), .clr_go(c5), .idle(id5));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t6 (.clk(clk), .rst_n(rst_n), .k(k6),
  .op_v(v6), .op_ext(e6), .op_x(x6), .op_cr(cr6), .ext_v(xv6), .ext_d(xd6), .root_key(rk6), .clr_go(c6), .idle(id6));
 ot_hgi_topk_heap_tile #(.MAX_K(2048), .MUT_BYP(MUT_BYP), .MUT_CLR(MUT_CLR)) u_t7 (.clk(clk), .rst_n(rst_n), .k(k7),
  .op_v(v7), .op_ext(e7), .op_x(x7), .op_cr(cr7), .ext_v(xv7), .ext_d(xd7), .root_key(rk7), .clr_go(c7), .idle(id7));
endmodule
`endif
