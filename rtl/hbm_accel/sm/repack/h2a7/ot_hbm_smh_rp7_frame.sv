`timescale 1ns/1ps
// Priced frame: north xo_b +3 is padded by six to align xo_g* +9.
// South external inputs and reset shift nine edges; all output ages are explicit.
module ot_hbm_smh_rp7_2 #(parameter integer VAR = 0, parameter integer HMUT = 0, parameter integer MUT = 0) (
    input wire clk, input wire rst_n, input wire [4:0] attn,
    input wire [8:0] xs_a1, input wire [4:0] xs_g1, input wire [6:0] xs_a2, input wire [4:0] xs_g2,
    input wire [8:0] xss_a1, input wire [4:0] xss_g1, input wire [6:0] xss_a2, input wire [4:0] xss_g2,
    input wire [817:0] rin_n, input wire [817:0] rin_s, input wire [2068:0] bin,
    output wire [817:0] rout_n, output wire [817:0] rout_s, output wire [2068:0] bout,
    input wire [99:0] gin, output wire [199:0] gout
);

wire [2068:0] x_b, x_bp; wire [49:0] x_g0; wire [99:0] x_gp;
ot_rp7_delay_ring #(.W(2069),.N(6)) u_xb_age (.clk(clk),.rst_n(rst_n),.d(x_b),.q(x_bp));
reg [8:0] sr; always @(posedge clk) sr<={sr[7:0],rst_n}; wire rst_s=sr[8];
wire [8:0] south_xss_a1;
ot_rp7_delay_ring #(.W(9),.N(9)) u_age_xss_a1 (.clk(clk),.rst_n(rst_n),.d(xss_a1),.q(south_xss_a1));
wire [4:0] south_xss_g1;
ot_rp7_delay_ring #(.W(5),.N(9)) u_age_xss_g1 (.clk(clk),.rst_n(rst_n),.d(xss_g1),.q(south_xss_g1));
wire [6:0] south_xss_a2;
ot_rp7_delay_ring #(.W(7),.N(9)) u_age_xss_a2 (.clk(clk),.rst_n(rst_n),.d(xss_a2),.q(south_xss_a2));
wire [4:0] south_xss_g2;
ot_rp7_delay_ring #(.W(5),.N(9)) u_age_xss_g2 (.clk(clk),.rst_n(rst_n),.d(xss_g2),.q(south_xss_g2));
wire [817:0] south_rin_s;
ot_rp7_delay_ring #(.W(818),.N(9)) u_age_rin_s (.clk(clk),.rst_n(rst_n),.d(rin_s),.q(south_rin_s));
wire [4:0] south_attn;
ot_rp7_delay_ring #(.W(5),.N(9)) u_age_attn (.clk(clk),.rst_n(rst_n),.d(attn),.q(south_attn));
generate if(VAR==0) begin:g_main
ot_hbm_smh_rp7n_m #(.HMUT(HMUT),.MUT(MUT)) u_n (.ck_m(clk), .ck_t(clk), .ck_tpw(clk), .ck_tpe(clk), .ck_cpw(clk), .ck_c(clk), .ck_cpe(clk), .ck_u(clk), .ck_xs(clk), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
ot_hbm_smh_rp7s_m #(.HMUT(HMUT),.MUT(MUT)) u_s (.ck_u(clk), .ck_upn(clk), .ck_upne(clk), .ck_c(clk), .ck_m(clk), .ck_cpw(clk), .ck_cpe(clk), .ck_xs(clk), .ck_mpse(clk), .rst_n(rst_s), .xss_a1(south_xss_a1), .xss_g1(south_xss_g1), .xss_a2(south_xss_a2), .xss_g2(south_xss_g2), .rin_s(south_rin_s), .attn(south_attn), .rout_s(rout_s), .gout(gout), .xi_b(x_bp), .xi_g0(x_g0), .xi_gp(x_gp));
end endgenerate
generate if(VAR==1) begin:g_fb
ot_hbm_smh_rp7n_f #(.HMUT(HMUT),.MUT(MUT)) u_n (.ck_c(clk), .ck_t(clk), .ck_tpw(clk), .ck_tpe(clk), .ck_cpw(clk), .ck_cw(clk), .ck_ce(clk), .ck_cpe(clk), .ck_u(clk), .ck_xs(clk), .rst_n(rst_n), .xs_a1(xs_a1), .xs_g1(xs_g1), .xs_a2(xs_a2), .xs_g2(xs_g2), .attn(attn), .rin_n(rin_n), .bin(bin), .gin(gin), .rout_n(rout_n), .bout(bout), .xo_b(x_b), .xo_g0(x_g0), .xo_gp(x_gp));
ot_hbm_smh_rp7s_f #(.HMUT(HMUT),.MUT(MUT)) u_s (.ck_t(clk), .ck_upn(clk), .ck_upne(clk), .ck_c(clk), .ck_cpw(clk), .ck_cw(clk), .ck_ce(clk), .ck_cpe(clk), .ck_u(clk), .ck_xs(clk), .ck_mpse(clk), .rst_n(rst_s), .xss_a1(south_xss_a1), .xss_g1(south_xss_g1), .xss_a2(south_xss_a2), .xss_g2(south_xss_g2), .rin_s(south_rin_s), .attn(south_attn), .rout_s(rout_s), .gout(gout), .xi_b(x_bp), .xi_g0(x_g0), .xi_gp(x_gp));
end endgenerate
endmodule
