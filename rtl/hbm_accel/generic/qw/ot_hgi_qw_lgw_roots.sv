`timescale 1ns/1ps
`default_nettype none
// Unselected WQ3 candidate. Preserve both closed WQ bodies and all existing
// registered input/output edges; expose separate clock roots from outer state.
// Actual parent/ownstate region/pins and coherent phi-R delivery remain open.
module ot_hgi_qw_lgw_roots (
    input  wire             clk_io,clk_wq0,clk_wq1,
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
    ot_rst_relay #(.REGIONS(1)) u_rst (.clk(clk_io), .rst_n_in(rst_n), .rst_n(rr_n));
    reg [7:0] f_wwq_cr, f_wwq_done;
    wire [8*280-1:0] t_wwq; reg [8*280-1:0] f_wwq;
    reg [8*15-1:0] wsec2; reg [8*4-1:0] ws2; (* keep *) reg [511:0] wy2; reg [7:0] wv2;
    wire [7:0] t_wcr, t_done;
    assign wwq = f_wwq;
    always @(posedge clk_io) begin
        f_wwq_cr <= wwq_cr; f_wwq_done <= wwq_done; f_wwq <= t_wwq; ws2 <= c_ws; wsec2 <= c_wsec; wy2 <= c_wy;
    end
    always @(posedge clk_io or negedge rr_n[0])
        if (!rr_n[0]) begin wv2 <= 0; e_wcr <= 0; e_done <= 0; end
        else begin wv2 <= c_wv; e_wcr <= t_wcr; e_done <= t_done; end
    wire[1:0]wq_clk={clk_wq1,clk_wq0};
    genvar q;
    generate for (q = 0; q < 2; q = q + 1) begin : g_q
        ot_hgi_qw_wq u_wq (.clk(wq_clk[q]), .rst_n(rst_n), .wwq(t_wwq[q*4*280 +: 4*280]), .wwq_cr(f_wwq_cr[q*4 +: 4]),
            .wwq_done(f_wwq_done[q*4 +: 4]), .c_y(wy2), .c_v(wv2[q*4 +: 4]), .c_slot(ws2[q*16 +: 16]), .c_sec(wsec2[q*60 +: 60]),
            .e_wcr(t_wcr[q*4 +: 4]), .e_done(t_done[q*4 +: 4]));
    end endgenerate
endmodule
`default_nettype wire
