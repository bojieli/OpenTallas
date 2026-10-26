// Existing bind178 ABI extensions extracted byte for byte from650532346d.
// These module names are absent from current canonical parents; no existing
// current module body is replaced. No added cycles versus selected source.
`timescale 1ns/1ps
module ot_s81_mu72_lnland_nst #(parameter integer MUT = 0) (
    input  wire         ck_k, ck_n, rs_k, rs_n,
    // K side (u_lep)
    input  wire         k_lo_v,  input  wire [552:0] k_lo_d, output wire k_lo_r,
    output wire         k_li_v,  output wire [552:0] k_li_d, input  wire k_li_r,
    input  wire         k_rxv,   output wire [2:0]   k_flt,
    // N side (u_ln)
    output wire         n_lo_v,  output wire [552:0] n_lo_d, input  wire n_lo_r,
    input  wire         n_li_v,  input  wire [552:0] n_li_d, output wire n_li_r,
    output wire         n_rxv,   input  wire [2:0]   n_flt
);
    wire [555:0] kn_i = {k_li_r, k_rxv, k_lo_v, k_lo_d}, kn_o;
    wire [556:0] nk_i = {n_flt, n_lo_r, n_li_v, n_li_d}, nk_o;
    ot_s81_mu72_land #(.W(556)) u_kn (.ck_w(ck_k), .ck_r(ck_n), .rs_w(rs_k), .rs_r(rs_n), .i(kn_i), .o(kn_o));
    ot_s81_mu72_land #(.W(557)) u_nk (.ck_w(ck_n), .ck_r(ck_k), .rs_w(rs_n), .rs_r(rs_k), .i(nk_i), .o(nk_o));
    wire [555:0] kn = (MUT == 1) ? kn_i : (MUT == 3) ? {kn_i[555], kn_o[554:0]} : kn_o;
    wire [556:0] nk = (MUT == 2) ? nk_i : nk_o;
    assign {n_li_r, n_rxv, n_lo_v, n_lo_d} = kn;
    assign {k_flt, k_lo_r, k_li_v, k_li_d} = nk;
endmodule
module ot_s81sl_lep_mu_ab_tpr #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [33:0]     mu_c,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    output wire [275:0]     tp_o
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(0), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(1), .NB(NB),
        .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .RT_EN(0), .IDX_EN(1), .IDX_TP(3)) u (   // L5B-LEPMU 10-21: native32 / face-stage opt-ins exposed (defaults 0 = unchanged)
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(2'b00), .l1_st(2'b00),
        .t_host(77'd0), .t_kd(54'd0), .f_host(), .f_lf(), .f_ks(),
        .mu_c(mu_c), .mu_rt(), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(lo2_v), .lo2_r(lo2_r), .lo2_d(lo2_d), .lo3_v(lo3_v), .lo3_r(lo3_r), .lo3_d(lo3_d),
        .li2_v(li2_v), .li2_r(li2_r), .li2_d(li2_d), .li3_v(li3_v), .li3_r(li3_r), .li3_d(li3_d), .rxvb(rxvb),
        .l2_f(l2_f), .l3_f(l3_f), .fault(fault), .tl(276'd0), .ca(tp_o), .cb());
endmodule


module ot_s81sl_lep_mu_hab_tp #(
    parameter integer DT = 512, parameter integer DR = 8, parameter integer CRED = 8, parameter integer SRAM = 1,
    parameter integer NB = 80, parameter integer RX_SRAM = 0, parameter integer IN_PIPE = 0, parameter integer NATIVE32 = 0
) (
    input  wire            clk,
    input  wire            rst_n,
    input  wire [1103:0]   ro,
    output wire [1103:0]   ri,
    output wire            lo0_v, input wire lo0_r, output wire [552:0] lo0_d,
    output wire            lo1_v, input wire lo1_r, output wire [552:0] lo1_d,
    input  wire            li0_v, output wire li0_r, input wire [552:0] li0_d,
    input  wire            li1_v, output wire li1_r, input wire [552:0] li1_d,
    output wire [1:0]      rxv,
    input  wire            sl_f,
    input  wire [2:0]      l0_f,
    input  wire [2:0]      l1_f,
    input  wire [1:0]      l0_st,
    input  wire [1:0]      l1_st,
    input  wire [76:0]     t_host,
    input  wire [53:0]     t_kd,
    output wire [514:0]    f_host,
    output wire [3:0]      f_lf,
    output wire [52:0]     f_ks,
    input  wire [33:0]     mu_c,
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            lo2_v, input wire lo2_r, output wire [552:0] lo2_d,
    output wire            lo3_v, input wire lo3_r, output wire [552:0] lo3_d,
    input  wire            li2_v, output wire li2_r, input wire [552:0] li2_d,
    input  wire            li3_v, output wire li3_r, input wire [552:0] li3_d,
    output wire [1:0]      rxvb,
    input  wire [2:0]      l2_f,
    input  wire [2:0]      l3_f,
    output wire            fault,
    input wire [275:0]     tp_i,
    output wire [275:0]    tp_o
);
    ot_s81sl_lep_core #(.DT(DT), .DR(DR), .CRED(CRED), .SRAM(SRAM), .HOST_EN(1), .MU_EN(1), .RX_SRAM(RX_SRAM), .AB_EN(1), .NB(NB),
        .IN_PIPE(IN_PIPE), .NATIVE32(NATIVE32), .IDX_EN(1), .IDX_TP(1)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri),
        .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v), .lo1_r(lo1_r), .lo1_d(lo1_d),
        .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r), .li1_d(li1_d), .rxv(rxv),
        .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st),
        .t_host(t_host), .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks),
        .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv), .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f),
        .lo2_v(lo2_v), .lo2_r(lo2_r), .lo2_d(lo2_d), .lo3_v(lo3_v), .lo3_r(lo3_r), .lo3_d(lo3_d),
        .li2_v(li2_v), .li2_r(li2_r), .li2_d(li2_d), .li3_v(li3_v), .li3_r(li3_r), .li3_d(li3_d), .rxvb(rxvb),
        .l2_f(l2_f), .l3_f(l3_f), .fault(fault), .tl(tp_i), .ca(tp_o), .cb());
endmodule
