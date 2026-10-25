`timescale 1ns/1ps
// STW-S81c-TOK4-BAND 10-22: lockstep shim for the banded gunit l1f.  Stands in for dsdv_gunit_l1f inside the dsdv_gunit
// golden bench (run_l1f_band_lsw.sh renames the current RTL's module to dsdv_gunit_l1f_ref): the BANDED flat parent
// dsdv_gunit_l1f_bp drives the outputs, the current RTL runs beside it on the same inputs, and every output is compared
// on every edge after reset.  Prints "GUNIT_LSW <inst> checked N mismatches M" at the end; first mismatches are listed.
module dsdv_gunit_l1f #(
    parameter integer MUT = 0
) (
    input  wire          clk,
    input  wire          rst_n,
    input  wire [5:0]    sa_r, input wire [223:0] sa_d, input wire [5:0] sb_r, input wire [223:0] sb_d,
    input  wire [13:0]   we,
    input  wire          c_go, input wire c_fw, input wire c_l, input wire [2:0] c_bn, input wire [4:0] c_lvn,
    input  wire          re, input wire [3:0] ra,
    input  wire [1:0]    bw_e, input wire [3:0] bw_a, input wire [255:0] bw_d,
    input  wire          g_go, input wire [5:0] g_hit, input wire [41:0] g_a,
    output wire          o_v, output wire o_f, output wire o_l, output wire o_g, output wire [244:0] o_d,   // RTLC 10-24: L1f o_d packed (d[205] dropped)
    output wire          o_flt
);
    wire r_v, r_f, r_l, r_g, r_flt; wire [244:0] r_d; wire [245:0] b_d;
    assign o_d = {b_d[245:206], b_d[204:0]};
    dsdv_gunit_l1f_bp #(.MUT(MUT)) u_b (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d),
        .we(we), .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn), .re(re), .ra(ra), .bw_e(bw_e),
        .bw_a(bw_a), .bw_d(bw_d), .g_go(g_go), .g_hit(g_hit), .g_a(g_a), .o_v(o_v), .o_f(o_f), .o_l(o_l), .o_g(o_g),
        .o_d(b_d), .o_flt(o_flt));
    dsdv_gunit_l1f_ref #(.MUT(MUT)) u_r (.clk(clk), .rst_n(rst_n), .sa_r(sa_r), .sa_d(sa_d), .sb_r(sb_r), .sb_d(sb_d),
        .we(we), .c_go(c_go), .c_fw(c_fw), .c_l(c_l), .c_bn(c_bn), .c_lvn(c_lvn), .re(re), .ra(ra), .bw_e(bw_e),
        .bw_a(bw_a), .bw_d(bw_d), .g_go(g_go), .g_hit(g_hit), .g_a(g_a), .o_v(r_v), .o_f(r_f), .o_l(r_l), .o_g(r_g),
        .o_d(r_d), .o_flt(r_flt));
    // o_d is only defined where the reference defines it: compare it when the reference's o_v / o_g say it carries data
    integer n_chk = 0, n_bad = 0, n_live = 0;
    reg armed = 1'b0;
    always @(posedge clk) begin
        if (rst_n) armed <= 1'b1;
        if (armed) begin
            n_chk = n_chk + 1;
            if (r_v || r_g) n_live = n_live + 1;
            if ({o_v, o_f, o_l, o_g, o_flt} !== {r_v, r_f, r_l, r_g, r_flt} || ((r_v || r_g) && o_d !== r_d)) begin
                n_bad = n_bad + 1;
                if (n_bad <= 4) $display("GUNIT_LSW %m MISMATCH edge %0d: band {v f l g flt}=%b ref=%b d_eq=%0d", n_chk,
                                         {o_v, o_f, o_l, o_g, o_flt}, {r_v, r_f, r_l, r_g, r_flt}, o_d === r_d);
            end
        end
    end
    final $display("GUNIT_LSW %m checked %0d live %0d mismatches %0d", n_chk, n_live, n_bad);
endmodule
