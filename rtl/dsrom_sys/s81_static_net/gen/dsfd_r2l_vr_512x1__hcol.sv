`timescale 1ns/1ps
module dsfd_r2l_vr_512x1__hcol (
    input wire [0:0] ck,
    output wire [514:0] o,
    input wire [0:0] rs,
    input wire [513:0] di0,
    input wire [0:0] fi0
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    wire [514:0] o_d;
    reg [513:0] dq0; always @(negedge fi0[0]) dq0 <= di0;   // pin register, falling forwarded edge
    wire [513:0] rc0 = dq0;
    wire [512:0] rq0; wire lv0, fl0;
    ot_s81_static_ratio_cross #(.W(513), .NS(4), .ND(3), .VBIT(0), .WRN(1)) u_0 (.w_ck(fi0[0]), .w_rst_n(rc0[0]), .i(rc0[513:1]), .r_ck(ck[0]), .r_rst_n(rsl), .o(rq0), .o_live(lv0), .fault(fl0));
    assign o_d[512:0] = {rq0[512:1], rq0[0] & lv0};
    assign o_d[514:513] = {fl0, lv0};   // {fault, live}
    reg [514:0] o_q; always @(posedge ck[0]) o_q <= o_d;   // output pin flop
    assign o = o_q;
endmodule
