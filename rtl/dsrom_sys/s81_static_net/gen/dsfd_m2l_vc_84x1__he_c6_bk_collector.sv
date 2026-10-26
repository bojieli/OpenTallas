`timescale 1ns/1ps
module dsfd_m2l_vc_84x1__he_c6_bk_collector (
    input wire [0:0] ck,
    output wire [86:0] o,
    input wire [0:0] rs,
    input wire [85:0] di0,
    input wire [0:0] fi0
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    wire [86:0] o_d;
    reg [85:0] dq0; always @(negedge fi0[0]) dq0 <= di0;   // pin register, falling forwarded edge
    wire [85:0] rc0 = dq0;
    wire [84:0] rq0; wire lv0, fl0;
    ot_s81_static_lane_end #(.W(85)) u_0 (.f_ck(fi0[0]), .i(rc0), .ck(ck[0]), .rst_n(rsl), .o(rq0), .live(lv0), .fault(fl0));
    assign o_d[84:0] = {rq0[84:1], rq0[0] & lv0};
    assign o_d[86:85] = {fl0, lv0};   // {fault, live}
    reg [86:0] o_q; always @(posedge ck[0]) o_q <= o_d;   // output pin flop
    assign o = o_q;
endmodule
