`timescale 1ns/1ps
`default_nettype none
// Wires-only data-head compatibility wrapper over gather and result/write leaves.
module ot_hgi_qw_ovd #(
    parameter integer LQ = 16
) (
    input  wire          clk,
    input  wire          rst_n,
    // lane-group leaves
    // lane-group leaves, one port set a leaf row (each on the face toward its row; the write data has one kept copy a row)
    input  wire [1023:0]     l_gp0, l_gp1, l_gp2, l_gp3,
    input  wire [7:0]        l_wcr0, l_wcr1, l_wcr2, l_wcr3,
    output wire [7:0]        l_wv0, l_wv1, l_wv2, l_wv3,
    output wire [8*15-1:0]   l_wsec0, l_wsec1, l_wsec2, l_wsec3,
    output wire [8*4-1:0]    l_ws0, l_ws1, l_ws2, l_ws3,
    output wire [511:0]      l_wy0, l_wy1, l_wy2, l_wy3,
    // control head
    input  wire              c_gv,
    input  wire [17:0]       c_gh,
    input  wire              c_mw_v,
    input  wire [5:0]        c_mw_a,
    input  wire [14:0]       c_mw_sec,
    input  wire [2:0]        c_mw_n,
    input  wire              c_wg,        // control head: busy && write grant, registered
    output wire               d_wf,
    output wire               d_bad,
    // decoder tiles (parent level)
    output wire              dec_rst_n,
    output wire               x_v,
    output wire  [17:0]       x_hd,
    output wire  [1023:0]     x,
    input  wire              d_vo,
    input  wire              d_f,
    input  wire              d_df,
    input  wire [511:0]      d_y
);
`ifdef OT_HARD_CHILDREN
 ot_hgi_qw_ovg u_g (
`else
 ot_hgi_qw_ovg u_g (
`endif
  .clk(clk),
  .rst_n(rst_n),
  .l_gp0(l_gp0),
  .l_gp1(l_gp1),
  .l_gp2(l_gp2),
  .l_gp3(l_gp3),
  .c_gv(c_gv),
  .c_gh(c_gh),
  .dec_rst_n(dec_rst_n),
  .x_v(x_v),
  .x_hd(x_hd),
  .x(x));
`ifdef OT_HARD_CHILDREN
 ot_hgi_qw_ovw u_w (
`else
 ot_hgi_qw_ovw #(.LQ(LQ)) u_w (
`endif
  .clk(clk),
  .rst_n(rst_n),
  .l_wcr0(l_wcr0),
  .l_wcr1(l_wcr1),
  .l_wcr2(l_wcr2),
  .l_wcr3(l_wcr3),
  .l_wv0(l_wv0),
  .l_wv1(l_wv1),
  .l_wv2(l_wv2),
  .l_wv3(l_wv3),
  .l_wsec0(l_wsec0),
  .l_wsec1(l_wsec1),
  .l_wsec2(l_wsec2),
  .l_wsec3(l_wsec3),
  .l_ws0(l_ws0),
  .l_ws1(l_ws1),
  .l_ws2(l_ws2),
  .l_ws3(l_ws3),
  .l_wy0(l_wy0),
  .l_wy1(l_wy1),
  .l_wy2(l_wy2),
  .l_wy3(l_wy3),
  .c_mw_v(c_mw_v),
  .c_mw_a(c_mw_a),
  .c_mw_sec(c_mw_sec),
  .c_mw_n(c_mw_n),
  .c_wg(c_wg),
  .d_wf(d_wf),
  .d_bad(d_bad),
  .d_vo(d_vo),
  .d_f(d_f),
  .d_df(d_df),
  .d_y(d_y));
endmodule
`default_nettype wire
