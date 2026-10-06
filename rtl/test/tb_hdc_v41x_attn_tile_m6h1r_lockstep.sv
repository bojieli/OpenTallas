`timescale 1ns/1ps
// Lockstep bench: the registered-parent H16 tile ot_attn_tile_m6h1r (16 x ot_attn_hgrp_m6h1, register tree in,
// capture out) against ot_hdc_v41x_attn_tile_l at the same configuration (H 16, TD 32, NBANK 5, BW 3, PWORDS 2,
// FPL 6; tile_l FML 6 = the leaves' FML 8 two cycles earlier) with every input, rst_n included, delayed RIN = 3
// cycles and the outputs a further 1 + 2 cycles.  Random stimulus as tb_hdc_v41x_attn_tile_s_lockstep; every output
// compared every cycle.  Prints TILERLOCK cycles=<n> mismatches=<m> ov=<valid outputs seen>; exits nonzero on any
// mismatch or if no output was compared.  NEG=1 swaps two heads' oy slots in the compare (negative control).
module tb_hdc_v41x_attn_tile_m6h1r_lockstep (input wire clk);
    localparam integer H = 16, TD = 32, NBANK = 5, BW = 3, PWORDS = 2, FPL = 6;
    parameter integer NCYC = 20000;
    parameter integer NEG = 0;
    parameter integer ROC = 1;
    parameter integer RMID = 0;
    parameter integer RV = 0;
    parameter integer HALF = 0;            // 1: two half tiles ot_attn_tile_m6h1h (RIN 2); 2: four quads ot_attn_tile_m6h1x (RIN 1); 3: the quad parent ot_attn_tile_m6h1p (RIN 3)
    localparam integer RIN = (HALF == 3) ? 3 : (HALF == 2) ? 1 : HALF ? 2 : 3 + RV + RMID, XD = 2 + (HALF ? 0 : ROC);
    reg rst_n = 1'b0;
    reg ld_v, ld_mode, ld_w2v, iv;
    reg [BW-1:0] ld_bank, ibank;
    reg [7:0] ld_grp;
    reg [PWORDS*TD*16-1:0] ld_w;
    reg [TD*18-1:0] ib;
    localparam integer PW = 1 + 1 + 1 + BW + 8 + PWORDS*TD*16 + 1 + 1 + BW + TD*18;
    wire [PW-1:0] pk_d;
    ot_hdc_v41x_dly #(.W(PW), .D(RIN)) u_id (.clk(clk), .d({rst_n, ld_v, ld_mode, ld_bank, ld_grp, ld_w, ld_w2v, iv, ibank, ib}),
                                           .q(pk_d));
    wire d_rst_n, d_ld_v, d_ld_mode, d_ld_w2v, d_iv;
    wire [BW-1:0] d_ld_bank, d_ibank;
    wire [7:0] d_ld_grp;
    wire [PWORDS*TD*16-1:0] d_ld_w;
    wire [TD*18-1:0] d_ib;
    assign {d_rst_n, d_ld_v, d_ld_mode, d_ld_bank, d_ld_grp, d_ld_w, d_ld_w2v, d_iv, d_ibank, d_ib} = pk_d;
    wire ov_l0, ov_l, ov_s;
    wire [H*32-1:0] oy_l0, oy_l, oy_s, oy_c;
    wire [H-1:0] of_l0, of_l, of_s;
    ot_hdc_v41x_attn_tile_l #(.H(H), .TD(TD), .NBANK(NBANK), .BW(BW), .PWORDS(PWORDS), .FPL(FPL), .FML(6)) u_l (
        .clk(clk), .rst_n(d_rst_n), .ld_v(d_ld_v), .ld_mode(d_ld_mode), .ld_bank(d_ld_bank), .ld_grp(d_ld_grp),
        .ld_w(d_ld_w), .ld_w2v(d_ld_w2v), .iv(d_iv), .ibank(d_ibank), .ib(d_ib), .ov(ov_l0), .oy(oy_l0), .oflt(of_l0));
    ot_hdc_v41x_dly #(.W(1 + H*32 + H), .D(XD)) u_xd (.clk(clk), .d({ov_l0, oy_l0, of_l0}), .q({ov_l, oy_l, of_l}));
    generate if (HALF == 3) begin : g_par
        ot_attn_tile_m6h1p u_s (
            .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
            .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov_s), .oy(oy_s), .oflt(of_s));
    end else if (HALF == 2) begin : g_quad
        ot_attn_tile_m6h1x u_s (
            .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
            .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov_s), .oy(oy_s), .oflt(of_s));
    end else if (HALF != 0) begin : g_half
        ot_attn_tile_m6h1h u_s (
            .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
            .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov_s), .oy(oy_s), .oflt(of_s));
    end else begin : g_full
        ot_attn_tile_m6h1r #(.ROC(ROC), .RMID(RMID), .RV(RV)) u_s (
        .clk(clk), .rst_n(rst_n), .ld_v(ld_v), .ld_mode(ld_mode), .ld_bank(ld_bank), .ld_grp(ld_grp), .ld_w(ld_w),
        .ld_w2v(ld_w2v), .iv(iv), .ibank(ibank), .ib(ib), .ov(ov_s), .oy(oy_s), .oflt(of_s));
    end endgenerate
    assign oy_c = (NEG != 0) ? {oy_s[H*32-1:64], oy_s[31:0], oy_s[63:32]} : oy_s;
    integer cyc = 0, mism = 0, nov = 0, i;
    function automatic [15:0] rbf16(input integer dummy);
        reg [15:0] x;
        begin
            x = $random;
            case ($urandom % 8)
                0: x[14:7] = 8'd0;                       // subnormal / zero
                1: x[14:7] = 8'hff;                      // nonfinite
                2: x[14:7] = 8'd120 + ($urandom % 16);   // near 1
                default: ;
            endcase
            rbf16 = x;
        end
    endfunction
    function automatic [17:0] relem(input integer dummy);
        reg [17:0] e;
        begin
            e = {$random} ;
            e[17] = (($urandom % 16) == 0);              // pad
            if (($urandom % 4) == 0) e[15:8] = 8'h7f;    // E4M3 NaN-ish codes
            if (($urandom % 4) == 0) e[7:0] = 8'd127 + ($urandom % 8) - 4;
            relem = e;
        end
    endfunction
    always @(posedge clk) begin
        cyc <= cyc + 1;
        if (cyc == 4) rst_n <= 1'b1;
        ld_v <= (($urandom % 3) == 0);
        ld_mode <= $urandom % 2;
        ld_w2v <= $urandom % 2;
        ld_bank <= $urandom % NBANK;
        ld_grp <= (($urandom % 8) == 0) ? $urandom : ($urandom % H);
        for (i = 0; i < PWORDS * TD; i = i + 1) ld_w[i*16 +: 16] <= rbf16(0);
        iv <= (($urandom % 4) != 0);
        ibank <= $urandom % NBANK;
        for (i = 0; i < TD; i = i + 1) ib[i*18 +: 18] <= relem(0);
        if (rst_n) begin
            if (ov_l) nov <= nov + 1;
            if (cyc > RIN + XD + 8 && (ov_l !== ov_s || oy_l !== oy_c || of_l !== of_s)) begin
                mism <= mism + 1;
                if (mism < 5) $display("MISMATCH cyc=%0d ov %b/%b oy %h / %h of %h / %h", cyc, ov_l, ov_s, oy_l, oy_s,
                                       of_l, of_s);
            end
        end
        if (cyc == NCYC) begin
            $display("TILERLOCK cycles=%0d mismatches=%0d ov=%0d", cyc, mism, nov);
            // nonzero exit on any mismatch, or if no output was ever compared (rule 2026-10-05)
            if (mism != 0 || nov == 0) $fatal(1, "TILERLOCK FAIL mismatches=%0d ov=%0d", mism, nov);
            $finish;
        end
    end
endmodule
