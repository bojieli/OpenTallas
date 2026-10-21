`timescale 1ns/1ps
// S81-SLICERTL (10-20): PARAMETER-FREE tops of the native32 MU LEP endpoints (MUBUF3 kits s81sl_lepmua_n32 /
// s81sl_lepmuh_n32 set RX_SRAM 1, IN_PIPE 1, NATIVE32 1 on ot_s81sl_lep_mu_a / _h; every other parameter = default).
// The die source (ot_s81sl_slice_lep_mu.sv) and the landed MU end-slice parents (landed/lep{e,w}_mu) instantiate THESE,
// so a die / parent bind of the hard view is exact: no #() on a hard child (a parameterised black box is renamed
// $paramod by Yosys and the default-parameter source would elaborate RX_SRAM 0 / IN_PIPE 0 / NATIVE32 0).  The n32 kit
// that closes must name the matching module here as its top with params {} (same elaboration, same netlist).
// Schedule: IN_PIPE 1 = +1 edge on ro, t_host, t_kd, mu_c (LEAD2-S81/LEPCAP; MU.S81.CAL / token calendar).

// ot_s81sl_lep_mu_a_n32 = ot_s81sl_lep_mu_a #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)): copy-A-only endpoint (s_0N, s_0S, s_7S; lepw_mu / lepw_mus / lepe_nh_mus)
module ot_s81sl_lep_mu_a_n32 (
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
    output wire [31:0]     mu_rt,
    output wire            ml_wv,
    output wire [1103:0]   ml_wd,
    input  wire            ml_rv,
    input  wire [1103:0]   ml_rd,
    input  wire            ml_f,
    output wire            fault
);
    ot_s81sl_lep_mu_a #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri), .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v),
        .lo1_r(lo1_r), .lo1_d(lo1_d), .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r),
        .li1_d(li1_d), .rxv(rxv), .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv),
        .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(fault)
    );
endmodule

// ot_s81sl_lep_mu_h_n32 = ot_s81sl_lep_mu_h #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)): host-plane endpoint (s_7N; lepe_mu)
module ot_s81sl_lep_mu_h_n32 (
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
    output wire            fault
);
    ot_s81sl_lep_mu_h #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri), .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v),
        .lo1_r(lo1_r), .lo1_d(lo1_d), .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r),
        .li1_d(li1_d), .rxv(rxv), .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st), .t_host(t_host),
        .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv),
        .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(fault)
    );
endmodule
