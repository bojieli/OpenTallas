`timescale 1ns/1ps
module dsfd_m2l_vs0_1x1__he_s6_bk_collector (
    input wire [0:0] ck,
    output wire [1:0] o,
    input wire [0:0] rs,
    input wire [3:0] xf,
    input wire [2:0] di0,
    input wire [0:0] fi0
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    reg [2:0] dq0; always @(negedge fi0[0]) dq0 <= di0;   // pin register, falling forwarded edge
    wire [2:0] rc0 = dq0;
    wire [1:0] rq0; wire lv0, fl0;
    ot_s81_static_lane_end #(.W(2)) u_0 (.f_ck(fi0[0]), .i(rc0), .ck(ck[0]), .rst_n(rsl), .o(rq0), .live(lv0), .fault(fl0));
    wire [1:0] o_d;
    assign o_d[0] = (rq0[0] & rq0[1]) | fl0 | xf[1] | xf[3];
    assign o_d[1] = rq0[0] & ~rq0[1] & lv0 & xf[0] & xf[2];
    reg [1:0] o_q; always @(posedge ck[0]) o_q <= o_d;   // output pin flop
    assign o = o_q;
endmodule
