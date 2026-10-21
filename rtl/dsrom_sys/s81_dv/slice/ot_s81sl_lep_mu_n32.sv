`timescale 1ns/1ps
// S81-SLICERTL (10-20) HARD-NOPARAM scheme: parameter-free ADAPTERS for the native32 MU LEP endpoints.  The endpoint kits
// (s81sl_lepmu{a,h}_n32, DRIVE-S81-LEPMU s81sl_lepmu{a,h}_r6{e,k,t}) close ot_s81sl_lep_mu_a / _h with RX_SRAM 1, IN_PIPE 1,
// NATIVE32 1; the die source (ot_s81sl_slice_lep_mu.sv) and the landed MU end-slice parents (landed/lep{e,w}_mu) instantiate
// these adapters with no #(), so:
//   RTL simulation (`ifndef OT_S81SL_HARD): the adapter elaborates the endpoint with EXACTLY the kit parameters;
//   hard build     (`define OT_S81SL_HARD, every S81 slice / cluster kit): the adapter instantiates the endpoint by module
//                  name with NO #() = the closed view (whose kit carries those parameters); no $paramod rename, no regate.
// The adapter is RTL glue (wires only), not a hard view: the hard child instance is u_lep.u.
// Schedule: IN_PIPE 1 = +1 edge on ro, t_host, t_kd, mu_c (LEAD2-S81/LEPCAP; MU.S81.CAL / token calendar).

// ot_s81sl_lep_mu_a_n32 = ot_s81sl_lep_mu_a #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) (adapter): copy-A-only endpoint (s_0N, s_0S, s_7S; lepw_mu / lepw_mus / lepe_nh_mus)
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
`ifndef OT_S81SL_HARD
    ot_s81sl_lep_mu_a #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri), .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v),
        .lo1_r(lo1_r), .lo1_d(lo1_d), .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r),
        .li1_d(li1_d), .rxv(rxv), .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv),
        .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(fault)
    );
`else
    ot_s81sl_lep_mu_a u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri), .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v),
        .lo1_r(lo1_r), .lo1_d(lo1_d), .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r),
        .li1_d(li1_d), .rxv(rxv), .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv),
        .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(fault)
    );
`endif
endmodule

// ot_s81sl_lep_mu_h_n32 = ot_s81sl_lep_mu_h #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) (adapter): host-plane endpoint (s_7N; lepe_mu)
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
`ifndef OT_S81SL_HARD
    ot_s81sl_lep_mu_h #(.RX_SRAM(1), .IN_PIPE(1), .NATIVE32(1)) u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri), .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v),
        .lo1_r(lo1_r), .lo1_d(lo1_d), .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r),
        .li1_d(li1_d), .rxv(rxv), .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st), .t_host(t_host),
        .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv),
        .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(fault)
    );
`else
    ot_s81sl_lep_mu_h u (
        .clk(clk), .rst_n(rst_n), .ro(ro), .ri(ri), .lo0_v(lo0_v), .lo0_r(lo0_r), .lo0_d(lo0_d), .lo1_v(lo1_v),
        .lo1_r(lo1_r), .lo1_d(lo1_d), .li0_v(li0_v), .li0_r(li0_r), .li0_d(li0_d), .li1_v(li1_v), .li1_r(li1_r),
        .li1_d(li1_d), .rxv(rxv), .sl_f(sl_f), .l0_f(l0_f), .l1_f(l1_f), .l0_st(l0_st), .l1_st(l1_st), .t_host(t_host),
        .t_kd(t_kd), .f_host(f_host), .f_lf(f_lf), .f_ks(f_ks), .mu_c(mu_c), .mu_rt(mu_rt), .ml_wv(ml_wv),
        .ml_wd(ml_wd), .ml_rv(ml_rv), .ml_rd(ml_rd), .ml_f(ml_f), .fault(fault)
    );
`endif
endmodule
