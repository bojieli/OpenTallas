`timescale 1ns/1ps
// dsfd_coll_core -- core TILE of the S81 collective slab (CLAUDE S81-PH coll v2): ot_s81ph_coll_core (EXT 1: TP4
// engine with SRAM FIFOs, VM input queues, output packer) + pin registers.  Lane interfaces lo (core -> lane i) /
// li (lane i -> core) through 2-slot skids at this tile's pins (valid / data / ready all registered), lane faults
// registered at the pin.  VM side as the v1 slab: f_vm / ts captured at the pin, t_vm from the core's register.
module dsfd_coll_core (
    input  wire [0:0]        ck,
    input  wire [0:0]        rs,          // stream reset (async assert), synchronised here
    input  wire [591:0]      f_vm,
    input  wire [2:0]        ts,
    output wire [2099:0]     t_vm,
    output wire [7:0]        lo_v,
    input  wire [7:0]        lo_r,
    output wire [8*553-1:0]  lo_d,
    input  wire [7:0]        li_v,
    output wire [7:0]        li_r,
    input  wire [8*553-1:0]  li_d,
    input  wire [23:0]       flt
);
    wire clk = ck[0];
    reg [1:0] rst_s;
    always @(posedge clk or negedge rs[0]) if (!rs[0]) rst_s <= 2'b00; else rst_s <= {rst_s[0], 1'b1};
    wire rst_n = rst_s[1];
    reg [591:0] fv_r; reg [2:0] ts_r; reg [23:0] flt_r;
    always @(posedge clk or negedge rst_n)
        if (!rst_n) begin fv_r <= 0; ts_r <= 0; flt_r <= 0; end
        else begin fv_r <= f_vm; ts_r <= ts; flt_r <= flt; end
    wire [7:0] x_lo_v, x_lo_r, x_lo_l, x_li_v, x_li_r, x_li_l;
    wire [8*552-1:0] x_lo_d, x_li_d;
    genvar l;
    generate for (l = 0; l < 8; l = l + 1) begin : g_l
        ot_s81ph_skid2 #(.W(553)) u_so (.clk(clk), .rst_n(rst_n), .in_v(x_lo_v[l]), .in_r(x_lo_r[l]),
            .in_d({x_lo_l[l], x_lo_d[l*552 +: 552]}), .out_v(lo_v[l]), .out_r(lo_r[l]), .out_d(lo_d[l*553 +: 553]));
        ot_s81ph_skid2 #(.W(553)) u_si (.clk(clk), .rst_n(rst_n), .in_v(li_v[l]), .in_r(li_r[l]), .in_d(li_d[l*553 +: 553]),
            .out_v(x_li_v[l]), .out_r(x_li_r[l]), .out_d({x_li_l[l], x_li_d[l*552 +: 552]}));
    end endgenerate
    ot_s81ph_coll_core #(.EXT(1)) u_core (.clk(clk), .rst_n(rst_n), .lane_rx({8*515{1'b0}}), .lane_tx(), .f_vm(fv_r),
        .ts(ts_r), .t_vm(t_vm), .fault(), .rank(), .eng_en(),
        .x_lo_v(x_lo_v), .x_lo_r(x_lo_r), .x_lo_d(x_lo_d), .x_lo_l(x_lo_l),
        .x_li_v(x_li_v), .x_li_r(x_li_r), .x_li_d(x_li_d), .x_li_l(x_li_l), .x_lflt(flt_r));
endmodule
