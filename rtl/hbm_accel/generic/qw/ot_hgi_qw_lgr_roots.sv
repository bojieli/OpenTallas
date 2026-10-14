`timescale 1ns/1ps
`default_nettype none
// Unselected WQ3 structural candidate. Existing RQ bodies retain exact state and
// edges, with separate clock pins from the3400-bit outer register bank.
// Each clock needs source-bound coherent phi-R delivery; no absolute slot grant.
module ot_hgi_qw_lgr_roots (
    input  wire             clk_io,clk_rq0,clk_rq1,
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
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk_io), .rst_n_in(rst_n), .rst_n(rr_n));
    reg [8*257-1:0] f_wrr; reg [7:0] f_wrq_cr;
    wire [8*16-1:0] t_wrq; reg [8*16-1:0] f_wrq;
    reg [8*15-1:0] rs2; reg [8*4-1:0] sl2; reg [7:0] hr2, hp2;
    wire [1023:0] gq [0:1]; wire [7:0] t_push, t_rcr;
    assign wrq = f_wrq;
    always @(posedge clk_io) begin
        f_wrr <= wrr; f_wrq_cr <= wrq_cr; f_wrq <= t_wrq; rs2 <= c_rs; sl2 <= c_sl;
        gp <= gq[0] | gq[1];
    end
    always @(posedge clk_io or negedge rr_n[0])
        if (!rr_n[0]) begin hr2 <= 0; hp2 <= 0; e_push <= 0; e_rcr <= 0; end
        else begin hr2 <= c_hit_r; hp2 <= c_hit_p; e_push <= t_push; e_rcr <= t_rcr; end
    wire[1:0]rq_clk={clk_rq1,clk_rq0};
    genvar q;
    generate for (q = 0; q < 2; q = q + 1) begin : g_q
        ot_hgi_qw_rq u_rq (.clk(rq_clk[q]), .rst_n(rst_n), .wrr(f_wrr[q*4*257 +: 4*257]), .wrq(t_wrq[q*64 +: 64]),
            .wrq_cr(f_wrq_cr[q*4 +: 4]), .c_hit_r(hr2[q*4 +: 4]), .c_sec(rs2[q*60 +: 60]), .c_hit_p(hp2[q*4 +: 4]),
            .c_slot(sl2[q*16 +: 16]), .gq(gq[q]), .e_push(t_push[q*4 +: 4]), .e_rcr(t_rcr[q*4 +: 4]));
    end endgenerate
endmodule

`default_nettype wire
