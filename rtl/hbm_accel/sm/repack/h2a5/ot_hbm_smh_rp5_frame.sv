`timescale 1ns/1ps
// HBM-OWN/SMH2 r5 (10-21): the SM frame slot with the two REGIONAL (landed) attention halves, every region clock on one
// bench clock (die form: each region root fed by the parent's region / landing).  VAR 0 = MAIN (x/c/m), 1 = FB (x/c).
// Bench DUT of tb_ot_hbm_smh_rp5_2 (lockstep vs ot_hbm_smh_rp4a_flat, gout + 18 (MAIN) / + 15 (FB) = r3 10 + r5 8 / 5).
module ot_hbm_smh_rp5_2 #(parameter integer VAR = 0, parameter integer HMUT = 0, parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [4:0] attn,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    input wire [99:0] gin, output wire [199:0] gout
);
    wire [2068:0] x_b; wire [49:0] x_g0; wire [99:0] x_gp;
    generate if (VAR == 0) begin : g_main
        ot_hbm_smh_rp5n_m #(.HMUT(HMUT), .MUT(MUT)) u_n (.ck_c(clk), .ck_x(clk), .ck_m(clk), .rst_n(rst_n), .xs_a1(xs_a1),
            .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n),
            .bout(bout), .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
        ot_hbm_smh_rp5s_m #(.HMUT(HMUT), .MUT(MUT)) u_s (.ck_c(clk), .ck_x(clk), .ck_m(clk), .rst_n(rst_n), .xss_a1(xss_a1),
            .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .attn(attn), .rin_s(rin_s), .rout_s(rout_s), .xi_b(x_b),
            .xi_g0(x_g0), .xi_gp(x_gp), .gout(gout));
    end else begin : g_fb
        ot_hbm_smh_rp5n_f #(.HMUT(HMUT), .MUT(MUT)) u_n (.ck_c(clk), .ck_x(clk), .rst_n(rst_n), .xs_a1(xs_a1),
            .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n),
            .bout(bout), .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
        ot_hbm_smh_rp5s_f #(.HMUT(HMUT), .MUT(MUT)) u_s (.ck_c(clk), .ck_x(clk), .rst_n(rst_n), .xss_a1(xss_a1),
            .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .attn(attn), .rin_s(rin_s), .rout_s(rout_s), .xi_b(x_b),
            .xi_g0(x_g0), .xi_gp(x_gp), .gout(gout));
    end endgenerate
endmodule
