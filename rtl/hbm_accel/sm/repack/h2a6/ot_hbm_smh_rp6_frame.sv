`timescale 1ns/1ps
// HBM-ELEM13/SMH-R6 r6 (10-21): the SM frame slot with the two GEOMETRIC regional (landed) attention halves, every band
// clock on one bench clock (die form: each band root fed by the parent's regional clock).  VAR 0 = MAIN (n t/u/c/m,
// s u/c/m), 1 = FB (n t/u/c, s t/u/c; merge on the column band).  Bench DUT of tb_ot_hbm_smh_rp6_2 (lockstep vs
// ot_hbm_smh_rp4a_flat: gout + 20 (MAIN) / + 15 (FB) = r3 10 + DG 10 / 5, rout + 1 (glue pin register), reset + 4).
module ot_hbm_smh_rp6_2 #(parameter integer VAR = 0, parameter integer HMUT = 0, parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [4:0] attn,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    input wire [99:0] gin, output wire [199:0] gout
);
    wire [2068:0] x_b; wire [49:0] x_g0; wire [99:0] x_gp;
    generate if (VAR == 0) begin : g_main
        ot_hbm_smh_rp6n_m #(.HMUT(HMUT), .MUT(MUT)) u_n (.ck_u(clk), .ck_t(clk), .ck_c(clk), .ck_m(clk), .rst_n(rst_n),
            .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin),
            .rout_n(rout_n), .bout(bout), .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
        ot_hbm_smh_rp6s_m #(.HMUT(HMUT), .MUT(MUT)) u_s (.ck_c(clk), .ck_u(clk), .ck_m(clk), .rst_n(rst_n), .xss_a1(xss_a1),
            .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .attn(attn), .rin_s(rin_s), .rout_s(rout_s), .xi_b(x_b),
            .xi_g0(x_g0), .xi_gp(x_gp), .gout(gout));
    end else begin : g_fb
        ot_hbm_smh_rp6n_f #(.HMUT(HMUT), .MUT(MUT)) u_n (.ck_u(clk), .ck_t(clk), .ck_c(clk), .rst_n(rst_n),
            .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin),
            .rout_n(rout_n), .bout(bout), .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
        ot_hbm_smh_rp6s_f #(.HMUT(HMUT), .MUT(MUT)) u_s (.ck_u(clk), .ck_t(clk), .ck_c(clk), .rst_n(rst_n), .xss_a1(xss_a1),
            .xss_g1(xss_g1), .xss_a2(xss_a2), .xss_g2(xss_g2), .attn(attn), .rin_s(rin_s), .rout_s(rout_s), .xi_b(x_b),
            .xi_g0(x_g0), .xi_gp(x_gp), .gout(gout));
    end endgenerate
endmodule
