`timescale 1ns/1ps
module dsfd_l2r_vr_512x1__hq_SW (
    input wire [0:0] ck,
    input wire [0:0] cks,
    output wire [0:0] fo,
    input wire [512:0] i,
    output wire [513:0] od,
    input wire [0:0] rs,
    input wire [0:0] rss,
    output wire [2:0] st
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    reg [1:0] rss__q; always @(posedge cks[0] or negedge rss[0]) if (!rss[0]) rss__q <= 2'b00; else rss__q <= {rss__q[0], 1'b1};
    wire rss_ = rss__q[1];
    reg [512:0] i_q; always @(posedge ck[0]) i_q <= i;   // input pin flop
    wire [512:0] w_ = i_q;
    assign fo = cks;
    wire [512:0] rq_; wire lv_, fl_;
    ot_s81_static_ratio_cross #(.W(513), .NS(3), .ND(4), .VBIT(0)) u_c (.w_ck(ck[0]), .w_rst_n(rsl), .i(w_), .r_ck(cks[0]), .r_rst_n(rss_), .o(rq_), .o_live(lv_), .fault(fl_));
    reg [513:0] od_q; always @(posedge cks[0]) od_q <= {rq_[512:1], rq_[0] & lv_, lv_};   // output pin flop
    (* async_reg = "true" *) reg [3:0] sy_; always @(posedge ck[0]) sy_ <= {sy_[1:0], fl_, lv_};
    reg [2:0] st_q; always @(posedge ck[0]) st_q <= {sy_[3], sy_[2], sy_[2]};   // {fault, live, live}
    assign od = od_q;
    assign st = st_q;
endmodule
