// REDESIGN-S81 2026-10-08: the pre-redesign hub end masters (dsfd_glue.sv at c206a1ac1), renamed old_*: bench reference.
module old_dsfd_l2r_vr_564x1__hx_W (
    input wire [0:0] ck,
    input wire [0:0] cks,
    output wire [0:0] fo,
    input wire [564:0] i,
    output wire [565:0] od,
    input wire [0:0] rs,
    input wire [0:0] rss,
    output wire [2:0] st
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    reg [1:0] rss__q; always @(posedge cks[0] or negedge rss[0]) if (!rss[0]) rss__q <= 2'b00; else rss__q <= {rss__q[0], 1'b1};
    wire rss_ = rss__q[1];
    wire wr, wl, rv, rl;
    wire [563:0] rd_;
    ot_ratio_cdc_fifo #(.W(564)) u_c (.wclk(ck[0]), .wrst_n(rsl), .w_v(i[0]), .w_rdy(wr), .w_d(i[564:1]), .rclk(cks[0]), .rrst_n(rss_), .r_v(rv), .r_rdy(1'b1), .r_d(rd_), .w_live(wl), .r_live(rl));
    assign fo = cks;
    assign od = {rd_, rv, rss_};
    assign st = {1'b0, wl, wr};
endmodule
module old_dsfd_r2l_vr_512x1__hcol (
    input wire [0:0] ck,
    output wire [514:0] o,
    input wire [0:0] rs,
    input wire [513:0] di0,
    input wire [0:0] fi0
);
    reg [1:0] rsl_q; always @(posedge ck[0] or negedge rs[0]) if (!rs[0]) rsl_q <= 2'b00; else rsl_q <= {rsl_q[0], 1'b1};
    wire rsl = rsl_q[1];
    wire rv0, rl0, wf0, rf0; wire [511:0] rq0;
    assign wf0 = 1'b0; assign rf0 = 1'b0;
    ot_ratio_cdc_fifo #(.W(512)) u_0 (.wclk(fi0[0]), .wrst_n(di0[0]), .w_v(di0[1]), .w_rdy(), .w_d(di0[513:2]), .rclk(ck[0]), .rrst_n(rsl), .r_v(rv0), .r_rdy(1'b1), .r_d(rq0), .w_live(), .r_live(rl0));
    assign o[512:0] = {rq0, rv0};
    assign o[514:513] = {wf0 | rf0, rl0};   // {fault, live}
endmodule
