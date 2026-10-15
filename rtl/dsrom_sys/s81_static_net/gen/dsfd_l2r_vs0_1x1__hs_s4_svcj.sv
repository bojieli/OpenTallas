`timescale 1ns/1ps
module dsfd_l2r_vs0_1x1__hs_s4_svcj (
    input wire [0:0] ck,
    input wire [0:0] cks,
    output wire [0:0] fo,
    input wire [1:0] i,
    output wire [2:0] od,
    input wire [0:0] rs,
    input wire [0:0] rss,
    input wire [7:0] xf
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    reg [1:0] rss__q; always @(posedge cks[0] or negedge rss[0]) if (!rss[0]) rss__q <= 2'b00; else rss__q <= {rss__q[0], 1'b1};
    wire rss_ = rss__q[1];
    reg [1:0] i_q; always @(posedge ck[0]) i_q <= i;   // input pin flop
    reg [7:0] x_q; always @(posedge ck[0]) x_q <= xf;   // input pin flop
    wire sf = i_q[0] | x_q[1] | x_q[3] | x_q[5] | x_q[7];
    wire so = i_q[1] & x_q[0] & x_q[2] & x_q[4] & x_q[6];
    wire [1:0] w_ = {sf, sf | so};   // {payload, valid}: written on its compiled slot, never queued
    assign fo = cks;
    reg [2:0] od_q; always @(posedge cks[0]) od_q <= {w_[1:1], w_[0] & rsl, rss_};   // output pin flop
    assign od = od_q;
endmodule
