`timescale 1ns/1ps
`default_nettype none
// Wires-only compatibility wrapper over result SRAM and four existing row stages.
module ot_hgi_qw_ovw #(
    parameter integer LQ = 16
) (
    input  wire          clk,
    input  wire          rst_n,
    // lane-group leaves
    // lane-group leaves, one port set a leaf row (each on the face toward its row; the write data has one kept copy a row)
    input  wire [7:0]        l_wcr0, l_wcr1, l_wcr2, l_wcr3,
    output wire [7:0]        l_wv0, l_wv1, l_wv2, l_wv3,
    output wire [8*15-1:0]   l_wsec0, l_wsec1, l_wsec2, l_wsec3,
    output wire [8*4-1:0]    l_ws0, l_ws1, l_ws2, l_ws3,
    output wire [511:0]      l_wy0, l_wy1, l_wy2, l_wy3,
    // control head
    input  wire              c_mw_v,
    input  wire [5:0]        c_mw_a,
    input  wire [14:0]       c_mw_sec,
    input  wire [2:0]        c_mw_n,
    input  wire              c_wg,        // control head: busy && write grant, registered
    output reg               d_wf,
    output reg               d_bad,
    // decoder tiles (parent level)
    input  wire              d_vo,
    input  wire              d_f,
    input  wire              d_df,
    input  wire [511:0]      d_y
);
    wire row_rst_n,wm_v;wire [14:0]wm_sec;wire [2:0]wm_n;wire [511:0]row_y;
`ifdef OT_HARD_CHILDREN
    ot_hgi_qw_ovr u_rf (
`else
    ot_hgi_qw_ovr #(.LQ(LQ)) u_rf (
`endif
      .clk(clk),.rst_n(rst_n),.l_wcr0(l_wcr0),.l_wcr1(l_wcr1),.l_wcr2(l_wcr2),.l_wcr3(l_wcr3),
      .c_mw_v(c_mw_v),.c_mw_a(c_mw_a),.c_mw_sec(c_mw_sec),.c_mw_n(c_mw_n),.c_wg(c_wg),
      .d_wf(d_wf),.d_bad(d_bad),.d_vo(d_vo),.d_f(d_f),.d_df(d_df),.d_y(d_y),
      .row_rst_n(row_rst_n),.wm_v(wm_v),.wm_sec(wm_sec),.wm_n(wm_n),.row_y(row_y));
    ot_hgi_qw_ovrow u_row0(.clk(clk),.rst_n(row_rst_n),.row_j(2'd0),.i_v(wm_v),.i_sec(wm_sec),.i_n(wm_n),.i_y(row_y),.o_v(l_wv0),.o_slot(l_ws0),.o_sec(l_wsec0),.o_y(l_wy0));
    ot_hgi_qw_ovrow u_row1(.clk(clk),.rst_n(row_rst_n),.row_j(2'd1),.i_v(wm_v),.i_sec(wm_sec),.i_n(wm_n),.i_y(row_y),.o_v(l_wv1),.o_slot(l_ws1),.o_sec(l_wsec1),.o_y(l_wy1));
    ot_hgi_qw_ovrow u_row2(.clk(clk),.rst_n(row_rst_n),.row_j(2'd2),.i_v(wm_v),.i_sec(wm_sec),.i_n(wm_n),.i_y(row_y),.o_v(l_wv2),.o_slot(l_ws2),.o_sec(l_wsec2),.o_y(l_wy2));
    ot_hgi_qw_ovrow u_row3(.clk(clk),.rst_n(row_rst_n),.row_j(2'd3),.i_v(wm_v),.i_sec(wm_sec),.i_n(wm_n),.i_y(row_y),.o_v(l_wv3),.o_slot(l_ws3),.o_sec(l_wsec3),.o_y(l_wy3));
endmodule
`default_nettype wire
