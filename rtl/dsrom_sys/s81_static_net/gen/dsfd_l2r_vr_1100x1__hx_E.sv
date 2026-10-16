`timescale 1ns/1ps
module dsfd_l2r_vr_1100x1__hx_E (
    input wire [0:0] ck,
    input wire [0:0] cks,
    output wire [0:0] fo,
    input wire [1100:0] i,
    output wire [565:0] oa,
    output wire [537:0] ob,
    input wire [0:0] rs,
    input wire [0:0] rss,
    output wire [2:0] st,
    output wire [0:0] fo2
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    reg [1:0] rss__q; always @(posedge cks[0] or negedge rss[0]) if (!rss[0]) rss__q <= 2'b00; else rss__q <= {rss__q[0], 1'b1};
    wire rss_ = rss__q[1];
    reg [1100:0] i_q; always @(posedge ck[0]) i_q <= i;   // input pin flop
    assign fo = cks;
    reg [1101:0] od_q; always @(posedge cks[0]) od_q <= {i_q[1100:1], i_q[0] & rsl, rss_};   // output pin flop
    reg [2:0] st_q; always @(posedge ck[0]) st_q <= {1'b0, rss_, rsl};
    assign fo2 = cks;
    assign oa = od_q[565:0];
    assign ob = {od_q[1101:566], od_q[1:0]};
    assign st = st_q;
endmodule
