`timescale 1ns/1ps
`default_nettype none
// Exact interface of selected50a9 HWINmux→f873MU47→8afseqhost.
// All realMU/status pins preserved. Source-only, no physical/wholeprogrammeclaim.
module dsdv_hostb_seqhost_mux #(parameter integer HOSTB_ENABLE=0) (
    input  wire          ck,
    input  wire          rst_n,
    input  wire [7:0]    tap_k, sink_k,
    input  wire [275:0]  vi_s, output wire [275:0] vo_s,
    input  wire [275:0]  vi_n, output wire [275:0] vo_n,
    input wire select_hbe,input wire [514:0] hbe_f_host,input wire [52:0] starter_f_ks,
    output wire [52:0] engram_f_ks,output wire [2:0] hostb_fault,
    input  wire [514:0]  f_host, output wire [76:0] t_host, input wire [3:0] f_lf,
    input  wire [52:0]   f_ks,   output wire [53:0] t_kd,
    output wire [3:0]    t_mf,
    output wire [32:0]   s_j,    input  wire [1:0]  s_jd_w, s_jd_e,
    output wire [291:0]  s_hw_w, s_hw_e, input wire [8:0] s_hc_w, s_hc_e,
    input  wire [1:0]    st_rg_w, st_rg_e,
    output wire          cw_v, output wire [9:0] cw_a, output wire [255:0] cw_d,
    output wire [33:0]   mu_c_7n, mu_c_7s, mu_c_0n, mu_c_0s,
    output wire [10:0]   mu_rc_7n, mu_rc_7s, mu_rc_0n, mu_rc_0s,
    input  wire [31:0]   mu_rt_7n, mu_rt_0n
);
 wire [514:0] landed_host;wire [52:0] landed_ks;
 dsdv_hostb_landing #(.ENABLE(HOSTB_ENABLE)) u_landing(.ck(ck),.rst_n(rst_n),.select_hbe(select_hbe),
 .legacy_f_host(f_host),.hbe_f_host(hbe_f_host),.legacy_f_ks(f_ks),.starter_f_ks(starter_f_ks),
 .seq_f_host(landed_host),.seq_f_ks(landed_ks),.engram_f_ks(engram_f_ks),.fault(hostb_fault));
 dsdv_seq_host_mux u_seqhost(.ck(ck),.rst_n(rst_n),.tap_k(tap_k),.sink_k(sink_k),.vi_s(vi_s),.vo_s(vo_s),.vi_n(vi_n),.vo_n(vo_n),
 .f_host(landed_host),.t_host(t_host),.f_lf(f_lf),.f_ks(landed_ks),.t_kd(t_kd),.t_mf(t_mf),.s_j(s_j),
 .s_jd_w(s_jd_w),.s_jd_e(s_jd_e),.s_hw_w(s_hw_w),.s_hw_e(s_hw_e),.s_hc_w(s_hc_w),.s_hc_e(s_hc_e),
 .st_rg_w(st_rg_w),.st_rg_e(st_rg_e),.cw_v(cw_v),.cw_a(cw_a),.cw_d(cw_d),
 .mu_c_7n(mu_c_7n),.mu_c_7s(mu_c_7s),.mu_c_0n(mu_c_0n),.mu_c_0s(mu_c_0s),
 .mu_rc_7n(mu_rc_7n),.mu_rc_7s(mu_rc_7s),.mu_rc_0n(mu_rc_0n),.mu_rc_0s(mu_rc_0s),.mu_rt_7n(mu_rt_7n),.mu_rt_0n(mu_rt_0n));
endmodule
`default_nettype wire
