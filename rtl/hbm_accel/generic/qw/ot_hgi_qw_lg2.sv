`timescale 1ns/1ps
`default_nettype none
// Lane-group leaf of the quant cluster (el1013-hbm-quant-split, 2026-10-13): hardened ONCE, instantiated 4 times.
// Lanes 8k..8k+7: the die-face pin flops of both directions, two read quads (ot_hgi_qw_rq), two write quads
// (ot_hgi_qw_wq), stage 2 of every head relay (pure pin flops) and the pair gather register gp = gq0 | gq1.
// Every port is a register on the leaf side; own clock root; no parameters (liberty blackbox at the parent).
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
    output reg  [1023:0]    gp,
    output reg  [7:0]       e_push, e_rcr, e_wcr, e_done
);
    wire [0:0] rr_n;
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk), .rst_n_in(rst_n), .rst_n(rr_n));
    reg [8*257-1:0] f_wrr; reg [7:0] f_wrq_cr, f_wwq_cr, f_wwq_done;
    wire [8*16-1:0] t_wrq; wire [8*280-1:0] t_wwq;
    reg [8*16-1:0] f_wrq; reg [8*280-1:0] f_wwq;
    reg [8*15-1:0] rs2, wsec2; reg [8*4-1:0] sl2, ws2; (* keep *) reg [511:0] wy2; reg [7:0] hr2, hp2, wv2;
    wire [1023:0] gq [0:1]; wire [7:0] t_push, t_rcr, t_wcr, t_done;
    assign wrq = f_wrq; assign wwq = f_wwq;
    always @(posedge clk) begin
        f_wrr <= wrr; f_wrq_cr <= wrq_cr; f_wwq_cr <= wwq_cr; f_wwq_done <= wwq_done; f_wrq <= t_wrq; f_wwq <= t_wwq;
        rs2 <= c_rs; sl2 <= c_sl; ws2 <= c_ws; wsec2 <= c_wsec; wy2 <= c_wy;
        gp <= gq[0] | gq[1];
    end
    always @(posedge clk or negedge rr_n[0])
        if (!rr_n[0]) begin hr2 <= 0; hp2 <= 0; wv2 <= 0; e_push <= 0; e_rcr <= 0; e_wcr <= 0; e_done <= 0; end
        else begin hr2 <= c_hit_r; hp2 <= c_hit_p; wv2 <= c_wv; e_push <= t_push; e_rcr <= t_rcr; e_wcr <= t_wcr; e_done <= t_done; end
    genvar q;
    generate for (q = 0; q < 2; q = q + 1) begin : g_q
        ot_hgi_qw_rq u_rq (.clk(clk), .rst_n(rst_n), .wrr(f_wrr[q*4*257 +: 4*257]), .wrq(t_wrq[q*64 +: 64]),
            .wrq_cr(f_wrq_cr[q*4 +: 4]), .c_hit_r(hr2[q*4 +: 4]), .c_sec(rs2[q*60 +: 60]), .c_hit_p(hp2[q*4 +: 4]),
            .c_slot(sl2[q*16 +: 16]), .gq(gq[q]), .e_push(t_push[q*4 +: 4]), .e_rcr(t_rcr[q*4 +: 4]));
        ot_hgi_qw_wq u_wq (.clk(clk), .rst_n(rst_n), .wwq(t_wwq[q*4*280 +: 4*280]), .wwq_cr(f_wwq_cr[q*4 +: 4]),
            .wwq_done(f_wwq_done[q*4 +: 4]), .c_y(wy2), .c_v(wv2[q*4 +: 4]), .c_slot(ws2[q*16 +: 16]), .c_sec(wsec2[q*60 +: 60]),
            .e_wcr(t_wcr[q*4 +: 4]), .e_done(t_done[q*4 +: 4]));
    end endgenerate
endmodule
`default_nettype wire
