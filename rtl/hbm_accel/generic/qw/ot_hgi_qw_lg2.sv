`timescale 1ns/1ps
`default_nettype none
// Lane-group of the quant cluster (el1013-hbm-quant-split, 2026-10-13), lanes 8k..8k+7.  WIRES ONLY since the physical
// plan put the read lanes on the cluster's W face and the write lanes on its E face (777.6 um apart): the group is two
// leaves with no signal between them, each hardened ONCE and instantiated 4 times, each with its own clock root:
//   ot_hgi_qw_lgr  read side : die-face pin flops (wrr in, wrq out), two read quads (ot_hgi_qw_rq, flat), stage 2 of
//                              the control head's read relays (pure pin flops), the pair gather register gp = gq0 | gq1
//   ot_hgi_qw_lgw  write side: die-face pin flops (wwq out), two write quads (ot_hgi_qw_wq, flat), stage 2 of the data
//                              head's write relays (pure pin flops)
// Every port is a register on the leaf side; no parameters (liberty blackbox at the parent).
module ot_hgi_qw_lg2 (
    input  wire             clk,
    input  wire             rst_n,
    input  wire [8*257-1:0] wrr,
    output wire [8*16-1:0]  wrq,
    input  wire [7:0]       wrq_cr,
    output wire [8*280-1:0] wwq,
    input  wire [7:0]       wwq_cr,
    input  wire [7:0]       wwq_done,
    input  wire [7:0]       c_hit_r, c_hit_p, c_wv,
    input  wire [8*15-1:0]  c_rs, c_wsec,
    input  wire [8*4-1:0]   c_sl, c_ws,
    input  wire [511:0]     c_wy,
    output wire [1023:0]    gp,
    output wire [7:0]       e_push, e_rcr, e_wcr, e_done
);
`ifdef OT_QW_LGR_ROOTS
    ot_hgi_qw_lgr_roots u_r (.clk_io(clk),.clk_rq0(clk),.clk_rq1(clk),
`else
    ot_hgi_qw_lgr u_r (.clk(clk),
`endif
        .rst_n(rst_n), .wrr(wrr), .wrq(wrq), .wrq_cr(wrq_cr), .c_hit_r(c_hit_r),
        .c_hit_p(c_hit_p), .c_rs(c_rs), .c_sl(c_sl), .gp(gp), .e_push(e_push), .e_rcr(e_rcr));
`ifdef OT_QW_LGW_ROOTS
    ot_hgi_qw_lgw_roots u_w (.clk_io(clk),.clk_wq0(clk),.clk_wq1(clk),
`else
    ot_hgi_qw_lgw u_w (.clk(clk),
`endif
        .rst_n(rst_n), .wwq(wwq), .wwq_cr(wwq_cr), .wwq_done(wwq_done), .c_wv(c_wv),
        .c_wsec(c_wsec), .c_ws(c_ws), .c_wy(c_wy), .e_wcr(e_wcr), .e_done(e_done));
endmodule

module ot_hgi_qw_lgr (
    input  wire             clk,
    input  wire             rst_n,
    input  wire [8*257-1:0] wrr,
    output wire [8*16-1:0]  wrq,
    input  wire [7:0]       wrq_cr,
    input  wire [7:0]       c_hit_r, c_hit_p,
    input  wire [8*15-1:0]  c_rs,
    input  wire [8*4-1:0]   c_sl,
    output reg  [1023:0]    gp,
    output reg  [7:0]       e_push, e_rcr
);
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg [8*257-1:0] f_wrr; reg [7:0] f_wrq_cr;
    wire [8*16-1:0] t_wrq; reg [8*16-1:0] f_wrq;
    reg [8*15-1:0] rs2; reg [8*4-1:0] sl2; reg [7:0] hr2, hp2;
    wire [1023:0] gq [0:1]; wire [7:0] t_push, t_rcr;
    assign wrq = f_wrq;
    always @(posedge clk) begin
        f_wrr <= wrr; f_wrq_cr <= wrq_cr; f_wrq <= t_wrq; rs2 <= c_rs; sl2 <= c_sl;
        gp <= gq[0] | gq[1];
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin hr2 <= 0; hp2 <= 0; e_push <= 0; e_rcr <= 0; end
        else begin hr2 <= c_hit_r; hp2 <= c_hit_p; e_push <= t_push; e_rcr <= t_rcr; end
    genvar q;
    generate for (q = 0; q < 2; q = q + 1) begin : g_q
        ot_hgi_qw_rq u_rq (.clk(clk), .rst_n(rst_n), .wrr(f_wrr[q*4*257 +: 4*257]), .wrq(t_wrq[q*64 +: 64]),
            .wrq_cr(f_wrq_cr[q*4 +: 4]), .c_hit_r(hr2[q*4 +: 4]), .c_sec(rs2[q*60 +: 60]), .c_hit_p(hp2[q*4 +: 4]),
            .c_slot(sl2[q*16 +: 16]), .gq(gq[q]), .e_push(t_push[q*4 +: 4]), .e_rcr(t_rcr[q*4 +: 4]));
    end endgenerate
endmodule

module ot_hgi_qw_lgw (
    input  wire             clk,
    input  wire             rst_n,
    output wire [8*280-1:0] wwq,
    input  wire [7:0]       wwq_cr,
    input  wire [7:0]       wwq_done,
    input  wire [7:0]       c_wv,
    input  wire [8*15-1:0]  c_wsec,
    input  wire [8*4-1:0]   c_ws,
    input  wire [511:0]     c_wy,
    output reg  [7:0]       e_wcr, e_done
);
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg [7:0] f_wwq_cr, f_wwq_done;
    wire [8*280-1:0] t_wwq; reg [8*280-1:0] f_wwq;
    reg [8*15-1:0] wsec2; reg [8*4-1:0] ws2; (* keep *) reg [511:0] wy2; reg [7:0] wv2;
    wire [7:0] t_wcr, t_done;
    assign wwq = f_wwq;
    always @(posedge clk) begin
        f_wwq_cr <= wwq_cr; f_wwq_done <= wwq_done; f_wwq <= t_wwq; ws2 <= c_ws; wsec2 <= c_wsec; wy2 <= c_wy;
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin wv2 <= 0; e_wcr <= 0; e_done <= 0; end
        else begin wv2 <= c_wv; e_wcr <= t_wcr; e_done <= t_done; end
    genvar q;
    generate for (q = 0; q < 2; q = q + 1) begin : g_q
        ot_hgi_qw_wq u_wq (.clk(clk), .rst_n(rst_n), .wwq(t_wwq[q*4*280 +: 4*280]), .wwq_cr(f_wwq_cr[q*4 +: 4]),
            .wwq_done(f_wwq_done[q*4 +: 4]), .c_y(wy2), .c_v(wv2[q*4 +: 4]), .c_slot(ws2[q*16 +: 16]), .c_sec(wsec2[q*60 +: 60]),
            .e_wcr(t_wcr[q*4 +: 4]), .e_done(t_done[q*4 +: 4]));
    end endgenerate
endmodule
`default_nettype wire
