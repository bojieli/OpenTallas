`timescale 1ns/1ps
module dsfd_l2r_vc_8x1__hs_hcSW (
    input wire [0:0] ck,
    input wire [0:0] cks,
    output wire [0:0] fo,
    input wire [8:0] i,
    output wire [9:0] od,
    input wire [0:0] rs,
    input wire [0:0] rss,
    output wire [2:0] st
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    reg [1:0] rss__q; always @(posedge cks[0] or negedge rss[0]) if (!rss[0]) rss__q <= 2'b00; else rss__q <= {rss__q[0], 1'b1};
    wire rss_ = rss__q[1];
    reg [8:0] i_q; always @(posedge ck[0]) i_q <= i;   // input pin flop
    wire [8:0] w_ = i_q;
    assign fo = cks;
    reg [9:0] od_q; always @(posedge cks[0]) od_q <= {w_[8:1], w_[0] & rsl, rss_};   // output pin flop
    reg [2:0] st_q; always @(posedge ck[0]) st_q <= {1'b0, rss_, rsl};   // output pin flop (observation)
    assign od = od_q;
    assign st = st_q;
endmodule
