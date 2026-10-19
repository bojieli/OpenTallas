`timescale 1ns/1ps
// RTL-BUILD-S81 (2026-10-18): composition bench of the end-slice masters.  Die A = ot_s81sl_slice_lepw (sid 0: S tier,
// column 0), die B = ot_s81sl_slice_lepe (sid 15: N tier, column 7; lepe_nh sid 14: S tier, column 7), lanes cross-wired through 2 x 2 ot_pdie_ucie.
// Line beats (kind CTL, slice mask 0 -> no slice acts on them) enter A's INWARD port ri_e with hops 3: A's unchanged ring
// stop forwards them out of its outward port (hops 2) into the link, B's ring stop receives them on its outward input
// ri_e and forwards them inward on ro_w with hops 1.  The reverse stream enters B's inward ri_w and leaves A's ro_e.
// Every beat must arrive bit-exact (header hops decremented twice, src kept), in order; no slice or link fault.
// S81-LEPV (10-18): +define+TB_SLEP_NH -> die B = ot_s81sl_slice_lepe_nh (s_7S master, no host ports); default die B =
// ot_s81sl_slice_lepe (s_7N master, host plane present, host inputs idle in this bench).
// S81-LBGAP G2 (10-18): sid = 2 * col + tier, the die straps (was 4'd7 under the old {tier, col} ring-stop decode).
`ifdef TB_SLEP_NH
`define TB_SLEP_E ot_s81sl_slice_lepe_nh
`define TB_SLEP_BSID 4'd14
`define TB_SLEP_EHOST
`else
`define TB_SLEP_E ot_s81sl_slice_lepe
`define TB_SLEP_BSID 4'd15
`define TB_SLEP_EHOST .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
`endif
module tb_s81sl_slice_lep #(parameter integer N = 200, parameter integer WAIT = 8000);
    reg clk = 0; always #0.4167 clk = ~clk;
    reg rst_n = 0;
    reg [1103:0] a_in = 0, b_in = 0; wire [1103:0] a_out, b_out, a_un, b_un;
    wire a_f, b_f;
    wire [511:0] atx0, atx1, btx0, btx1, arx0, arx1, brx0, brx1; wire [1:0] ast0, ast1, bst0, bst1;
    wire [512:0] pa0, pa1, pb0, pb1; wire ta0, ta1, tb0, tb1;
    ot_s81sl_slice_lepw A (.clk(clk), .rst_n(rst_n), .sid(4'd0), .ri_e(a_in), .ro_e(a_out), .vi(276'd0), .vo(), .bi(1104'd0),
        .bo(), .xc(), .rt(560'd0), .ck_line(), .ck_v(), .ck_xc(), .ck_rt(), .ch_b(1'b0), .tx0(atx0), .tx1(atx1),
        .rx0({ast0, arx0}), .rx1({ast1, arx1}), .tf(),
        .fault(a_f));                                       // S81-LEPV: lepw has no host plane (HOST_EN 0)
    `TB_SLEP_E B (.clk(clk), .rst_n(rst_n), .sid(`TB_SLEP_BSID), .ri_w(b_in), .ro_w(b_out), .vi(276'd0), .vo(), .bi(1104'd0),
        .bo(), .xc(), .rt(560'd0), .ck_line(), .ck_v(), .ck_xc(), .ck_rt(), .ch_b(1'b0), .tx0(btx0), .tx1(btx1),
        .rx0({bst0, brx0}), .rx1({bst1, brx1}), .tf(),
        `TB_SLEP_EHOST .fault(b_f));
    ot_pdie_ucie #(.PMA_LAT(2)) ua0 (.clk(clk), .rst(rst_n), .tx(atx0), .rx(arx0), .st(ast0), .pma_tx(pa0), .pma_tck(ta0), .pma_rx(pb0), .pma_rck(tb0));
    ot_pdie_ucie #(.PMA_LAT(2)) ub0 (.clk(clk), .rst(rst_n), .tx(btx0), .rx(brx0), .st(bst0), .pma_tx(pb0), .pma_tck(tb0), .pma_rx(pa0), .pma_rck(ta0));
    ot_pdie_ucie #(.PMA_LAT(5)) ua1 (.clk(clk), .rst(rst_n), .tx(atx1), .rx(arx1), .st(ast1), .pma_tx(pa1), .pma_tck(ta1), .pma_rx(pb1), .pma_rck(tb1));
    ot_pdie_ucie #(.PMA_LAT(5)) ub1 (.clk(clk), .rst(rst_n), .tx(btx1), .rx(brx1), .st(bst1), .pma_tx(pb1), .pma_tck(tb1), .pma_rx(pa1), .pma_rck(ta1));
    reg [1103:0] qa [0:1023]; reg [1103:0] qb [0:1023];
    integer na = 0, nb = 0, ra = 0, rb = 0, bad = 0, cyc = 0, other = 0;
    function automatic [1103:0] cbeat(input [3:0] src);
        integer i; reg [1103:0] b;
        begin
            for (i = 0; i < 34; i = i + 1) b[i * 32 +: 32] = $urandom; b[1103:1088] = $urandom;
            b[0] = 1'b1; b[3:1] = 3'd0; b[8:4] = 5'd3; b[12:9] = src; b[21 +: 16] = 16'd0;   // CTL, hops 3, mask 0
            cbeat = b;
        end
    endfunction
    function automatic [1103:0] hop1(input [1103:0] b); begin hop1 = b; hop1[8:4] = 5'd1; end endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (b_out[0]) begin
            if (ra >= na || b_out !== hop1(qa[ra])) begin bad = bad + 1; if (bad < 6) $display("MISMATCH A->B %0d cyc %0d %h", ra, cyc, b_out[63:0]); end
            ra = ra + 1;
        end
        if (a_out[0]) begin
            if (rb >= nb || a_out !== hop1(qb[rb])) begin bad = bad + 1; if (bad < 6) $display("MISMATCH B->A %0d cyc %0d %h", rb, cyc, a_out[63:0]); end
            rb = rb + 1;
        end
    end
    initial begin
        repeat (8) @(posedge clk); rst_n = 1;
        repeat (WAIT) @(posedge clk);
        while (na < N || nb < N) begin
            @(negedge clk); a_in = 0; b_in = 0;
            if (na < N && ($urandom % 100) < 50) begin a_in = cbeat(4'd5); qa[na] = a_in; na = na + 1; end
            if (nb < N && ($urandom % 100) < 50) begin b_in = cbeat(4'd9); qb[nb] = b_in; nb = nb + 1; end
        end
        @(negedge clk); a_in = 0; b_in = 0;
        repeat (3000) @(posedge clk);
        $display("SLEP_STATS A->B %0d/%0d B->A %0d/%0d mismatches %0d fault A %0d B %0d", ra, na, rb, nb, bad, a_f, b_f);
        if (bad == 0 && ra == N && rb == N && !a_f && !b_f)
            $display("PASS slice_lep: %0d + %0d line beats crossed W-end -> E-end and back through the slice ring stops + UCIe lanes bit-exact", ra, rb);
        else $display("FAIL slice_lep");
        $finish;
    end
endmodule
